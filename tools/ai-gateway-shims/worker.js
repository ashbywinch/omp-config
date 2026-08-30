// AI Gateway provider shim: dynamic-route model nodes call custom providers at
// the forced OpenAI path {origin}/v1/chat/completions (the gateway ignores the
// base_url path — see skills/cloudflare-ai-gateway/references/adding-providers.md).
// Providers that serve OpenAI-compatible chat completions at a different path
// need this shim: it rewrites that one path to UPSTREAM.
//
// No provider secrets live here: the gateway attaches the provider's BYOK key
// as the Authorization header on its upstream call, and we forward it
// untouched. Access control: when the SHIM_TOKEN secret is set, callers must
// carry the same value in x-shim-token (put it in the custom provider's
// `headers` field so the gateway attaches it automatically).
//
// Deploy: ./deploy.sh  (deploys the zai and opencode environments)

export default {
	async fetch(request, env) {
		const url = new URL(request.url);

		if (request.method !== "POST" || url.pathname !== "/v1/chat/completions") {
			return new Response(
				JSON.stringify({ error: { message: "Not Found", type: "invalid_request_error" } }),
				{ status: 404, headers: { "content-type": "application/json" } },
			);
		}

		if (!env.SHIM_TOKEN || request.headers.get("x-shim-token") !== env.SHIM_TOKEN) {
			return new Response(
				JSON.stringify({ error: { message: "Unauthorized", type: "authentication_error" } }),
				{ status: 401, headers: { "content-type": "application/json" } },
			);
		}

		// Abort below the gateway's model-node timeout so a hung upstream 502s
		// and the route's fallback cascade fires instead of stalling.
		const controller = new AbortController();
		const timer = setTimeout(() => controller.abort(), Number(env.UPSTREAM_TIMEOUT_MS || 300000));

		try {
			// Forward only what the provider needs — the caller's hop-by-hop and
			// Cloudflare-internal headers must not leak upstream.
			const headers = new Headers();
			for (const name of ["authorization", "content-type", "accept", "user-agent"]) {
				const value = request.headers.get(name);
				if (value) headers.set(name, value);
			}
			const upstream = await fetch(env.UPSTREAM, {
				method: "POST",
				headers,
				body: request.body,
				signal: controller.signal,
			});

			const contentType = upstream.headers.get("content-type") || "";
			// Some providers return business errors as HTTP 200 with a JSON error
			// body (z.ai does this for auth and quota). Remap those to 502 so the
			// gateway's fallback cascade fires; stream everything else (SSE
			// included) untouched.
			if (upstream.status >= 200 && upstream.status < 300 && contentType.includes("application/json")) {
				const bodyText = await upstream.text();
				let isError = false;
				try {
					const parsed = JSON.parse(bodyText);
					isError = Boolean(
						parsed &&
						(parsed.error ||
							parsed.success === false ||
							(typeof parsed.code === "number" && parsed.code !== 0 && parsed.code !== 200)),
					);
				} catch {}
				const headers = new Headers(upstream.headers);
				headers.delete("content-length");
				return new Response(bodyText, {
					status: isError ? 502 : upstream.status,
					statusText: upstream.statusText,
					headers,
				});
			}

			return new Response(upstream.body, {
				status: upstream.status,
				statusText: upstream.statusText,
				headers: upstream.headers,
			});
		} catch (err) {
			const aborted = err?.name === "AbortError";
			return new Response(
				JSON.stringify({
					error: {
						message: aborted ? "upstream_timeout" : `upstream_error: ${String(err)}`,
						type: "upstream_error",
					},
				}),
				{ status: 502, headers: { "content-type": "application/json" } },
			);
		} finally {
			clearTimeout(timer);
		}
	},
};
