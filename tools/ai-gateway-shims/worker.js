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
// forwarded with no per-chunk parsing — the only per-chunk work is a timeout
// re-arm; the only buffering is the whole body of non-SSE JSON responses and
// the first SSE event (both small).
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
		// Re-armed on every streamed chunk (inactivity timeout), so a stream
		// that stalls mid-body is still bounded. A non-numeric or non-positive
		// UPSTREAM_TIMEOUT_MS falls back to the default instead of NaN (which
		// setTimeout treats as 0 — aborting every request instantly).
		const configured = Number(env.UPSTREAM_TIMEOUT_MS);
		const timeoutMs = Number.isFinite(configured) && configured > 0 ? configured : 300000;
		const controller = new AbortController();
		let timer = setTimeout(() => controller.abort(), timeoutMs);
		const arm = () => {
			clearTimeout(timer);
			timer = setTimeout(() => controller.abort(), timeoutMs);
		};

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

			// Non-SSE JSON: buffer and validate. This shim only serves
			// /v1/chat/completions, so a healthy 2xx body has a non-empty
			// choices array — anything else (z.ai auth/quota error bodies,
			// empty bodies, unparseable junk, empty choices) must 502 so the
			// route cascade fires.
			if (upstream.status >= 200 && upstream.status < 300 && contentType.includes("application/json")) {
				const bodyText = await upstream.text();
				let parsed = null;
				try { parsed = JSON.parse(bodyText); } catch {}
				const isError = !parsed || !Array.isArray(parsed.choices) || parsed.choices.length === 0;
				if (isError) {
					console.log(JSON.stringify({ event: "provider_error_remapped", upstream_status: upstream.status, body: bodyText.slice(0, 300) }));
					return errorResponse(502, "provider returned an error response");
				}
				// bodyText is decoded text: drop length/encoding headers that
				// describe the wire bytes, or the gateway tries to inflate it.
				const passthrough = new Headers(upstream.headers);
				passthrough.delete("content-length");
				passthrough.delete("content-encoding");
				return new Response(bodyText, {
					status: upstream.status,
					statusText: upstream.statusText,
					headers: passthrough,
				});
			}

			// Streams (SSE etc.): an empty stream must 502 (cascade) instead of
			// completing as an empty 200, and a leading error event must not
			// stream through as if it were content. Buffer until the first SSE
			// event is complete (\r?\n\r?\n) so an error event split across
			// transport chunks still 502s; the 64 KiB cap bounds a pathological
			// upstream. Everything after the gate streams through untouched.
			if (upstream.body) {
				const reader = upstream.body.getReader();
				const decoder = new TextDecoder();
				const buffered = [];
				let scan = "";
				while (scan.length < 65536 && !/\r?\n\r?\n/.test(scan)) {
					const { done, value } = await reader.read();
					if (done) break;
					buffered.push(value);
					scan += decoder.decode(value, { stream: true });
				}
				if (buffered.length === 0) {
					console.log(JSON.stringify({ event: "empty_stream", upstream_status: upstream.status }));
					return errorResponse(502, "empty response from provider");
				}
				if (scan.includes('"error"') && !scan.includes('"choices"')) {
					console.log(JSON.stringify({ event: "provider_error_stream", first: scan.slice(0, 300) }));
					return errorResponse(502, "provider returned an error response");
				}
				const stream = new ReadableStream({
					async start(streamController) {
						try {
							for (const chunk of buffered) {
								streamController.enqueue(chunk);
								arm();
							}
							for (;;) {
								const next = await reader.read();
								if (next.done) break;
								streamController.enqueue(next.value);
								arm();
							}
							clearTimeout(timer);
							streamController.close();
						} catch (err) {
							clearTimeout(timer);
							streamController.error(err);
						}
					},
					cancel(reason) {
						clearTimeout(timer);
						try { reader.cancel(reason); } catch {}
						controller.abort();
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
