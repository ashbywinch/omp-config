// AI Gateway provider shim: dynamic-route model nodes call custom providers at
// the forced OpenAI path {origin}/v1/chat/completions (the gateway ignores the
// base_url path — see skills/cloudflare-ai-gateway/references/adding-providers.md).
// Providers that serve OpenAI-compatible chat completions at a different path
// need this shim: it rewrites that one path to UPSTREAM.
//
// No provider secrets live here: the gateway attaches the provider's BYOK key
// as the Authorization header on its upstream call, and we forward it
// untouched. Access control: the SHIM_TOKEN secret must be set — the guard
// fails closed, so a misconfigured deploy returns 401 instead of proxying to
// a paid upstream. Mirror the token in the custom provider's `headers` field
// so the gateway attaches it automatically.
//
// Behavior beyond the rewrite (so route fallbacks actually fire):
// - Providers that deliver business errors as HTTP 200 (z.ai does this for
//   auth and quota, and sends them without a choices array) are remapped
//   to 502.
// - Empty provider responses (a 200 that carries no body bytes) are remapped
//   to 502 — degraded z.ai states otherwise surface to the client as a
//   silent empty answer.
//
// CPU discipline: Workers free tier caps CPU at 10ms/request. Streams are
// forwarded with no per-chunk work; the only buffering is the whole body of
// non-SSE JSON responses and the first chunk of SSE streams (both small).
//
// Deploy: ./deploy.sh (deploys the zai and opencode environments).

const FORWARDED = ["authorization", "content-type", "accept", "user-agent"];

function errorResponse(status, message) {
	return new Response(
		JSON.stringify({ error: { message, type: "upstream_error" } }),
		{ status, headers: { "content-type": "application/json" } },
	);
}

export default {
	async fetch(request, env) {
		const url = new URL(request.url);

		if (request.method !== "POST" || url.pathname !== "/v1/chat/completions") {
			return errorResponse(404, "Not Found");
		}

		if (!env.SHIM_TOKEN || request.headers.get("x-shim-token") !== env.SHIM_TOKEN) {
			return errorResponse(401, "Unauthorized");
		}

		// Abort a hung upstream so the route's fallback cascade fires instead of
		// stalling; sits at/below the model-node timeout of the routes served.
		const controller = new AbortController();
		const timer = setTimeout(() => controller.abort(), Number(env.UPSTREAM_TIMEOUT_MS || 300000));

		try {
			const headers = new Headers();
			for (const name of FORWARDED) {
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

			// Non-SSE JSON: buffer and validate. z.ai reports auth/quota business
			// errors as 200 with an error-shaped body (no choices array), and
			// degraded states as empty bodies. Both must 502 so the route
			// cascade fires.
			if (upstream.status >= 200 && upstream.status < 300 && contentType.includes("application/json")) {
				const bodyText = await upstream.text();
				const empty = !bodyText.trim();
				let isError = empty;
				if (!empty) {
					let parsed = null;
					try { parsed = JSON.parse(bodyText); } catch {}
					isError = Boolean(
						parsed && !Array.isArray(parsed.choices) &&
						(parsed.error || parsed.success === false ||
							(typeof parsed.code === "number" && parsed.code !== 0 && parsed.code !== 200)),
					);
				}
				if (isError) {
					console.log(JSON.stringify({ event: "provider_error_remapped", upstream_status: upstream.status, body: bodyText.slice(0, 300) }));
					return errorResponse(502, "provider returned an error response");
				}
				return new Response(bodyText, {
					status: upstream.status,
					statusText: upstream.statusText,
					headers: upstream.headers,
				});
			}

			// Streams (SSE etc.): gate on the first chunk — an empty stream must
			// 502 (cascade) instead of completing as an empty 200, and a leading
			// error event must not stream through as if it were content.
			// Everything after the first chunk streams through with no
			// per-chunk work.
			if (upstream.body) {
				const reader = upstream.body.getReader();
				const first = await reader.read();
				if (first.done) {
					console.log(JSON.stringify({ event: "empty_stream", upstream_status: upstream.status }));
					return errorResponse(502, "empty response from provider");
				}
				const firstText = new TextDecoder().decode(first.value.slice(0, 2048));
				if (firstText.includes('"error"') && !firstText.includes('"choices"')) {
					console.log(JSON.stringify({ event: "provider_error_stream", first: firstText.slice(0, 300) }));
					return errorResponse(502, "provider returned an error response");
				}
				const stream = new ReadableStream({
					async start(controller) {
						try {
							controller.enqueue(first.value);
							for (;;) {
								const next = await reader.read();
								if (next.done) break;
								controller.enqueue(next.value);
							}
							controller.close();
						} catch (err) {
							controller.error(err);
						}
					},
					cancel(reason) {
						try { reader.cancel(reason); } catch {}
					},
				});
				return new Response(stream, {
					status: upstream.status,
					statusText: upstream.statusText,
					headers: upstream.headers,
				});
			}

			console.log(JSON.stringify({ event: "empty_response", upstream_status: upstream.status }));
			return errorResponse(502, "empty response from provider");
		} catch (err) {
			const aborted = err?.name === "AbortError";
			return errorResponse(502, aborted ? "upstream_timeout" : `upstream_error: ${String(err)}`);
		} finally {
			clearTimeout(timer);
		}
	},
};
