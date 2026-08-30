// AI Gateway provider shim: dynamic-route model nodes call custom providers at
// the forced OpenAI path {origin}/v1/chat/completions (the gateway ignores the
// base_url path — see skills/cloudflare-ai-gateway/references/adding-providers.md).
// Providers that serve OpenAI-compatible chat completions at a different path
// need this shim: it rewrites that one path to UPSTREAM.
//
// No secrets live here: the gateway attaches the provider's BYOK key as the
// Authorization header on its upstream call, and we forward it untouched.
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

		try {
			const upstream = await fetch(env.UPSTREAM, {
				method: "POST",
				headers: request.headers,
				body: request.body,
			});
			// Stream the response (SSE included) back to the gateway.
			return new Response(upstream.body, {
				status: upstream.status,
				statusText: upstream.statusText,
				headers: upstream.headers,
			});
		} catch (err) {
			return new Response(
				JSON.stringify({ error: { message: `upstream_error: ${String(err)}`, type: "upstream_error" } }),
				{ status: 502, headers: { "content-type": "application/json" } },
			);
		}
	},
};
