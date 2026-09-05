// Tests for the AI Gateway provider shim. The upstream is always a fake —
// globalThis.fetch is stubbed, so nothing here touches the network.
// Run: bun test
import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import worker from "./worker.js";

const TOKEN = "test-shim-token";
const UPSTREAM = "https://upstream.test/v1/chat/completions";
const env = {
	SHIM_TOKEN: TOKEN,
	UPSTREAM,
	UPSTREAM_TIMEOUT_MS: "5000",
};

function shimRequest(body, headers = {}) {
	return new Request("https://shim.test/v1/chat/completions", {
		method: "POST",
		headers: { "content-type": "application/json", "x-shim-token": TOKEN, ...headers },
		body: typeof body === "string" ? body : JSON.stringify(body),
	});
}

const completion = (reasoning = "thinking") => ({
	choices: [{ index: 0, message: { role: "assistant", content: "ok", reasoning_content: reasoning }, finish_reason: "stop" }],
	usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
});

const sseResponse = (events, status = 200) => {
	const body = events.map((e) => `data: ${e}\n\n`).join("") + "data: [DONE]\n\n";
	return new Response(body, { status, headers: { "content-type": "text/event-stream" } });
};
let captured;
const fakeUpstream = (response) => {
	captured = undefined;
	return async (url, init) => {
		captured = { url, headers: init.headers, body: init.body, signal: init.signal };
		return response instanceof Error ? Promise.reject(response) : response;
	};
};

let originalFetch;
beforeEach(() => {
	originalFetch = globalThis.fetch;
});
afterEach(() => {
	globalThis.fetch = originalFetch;
});

describe("ai-gateway provider shim", () => {
	it("404s non-chat-completions paths", async () => {
		globalThis.fetch = fakeUpstream(new Response("x"));
		const res = await worker.fetch(new Request("https://shim.test/v1/embeddings", { method: "POST", headers: { "x-shim-token": TOKEN }, body: "{}" }), env);
		expect(res.status).toBe(404);
	});

	it("fails closed with 401 when the x-shim-token header is missing", async () => {
		globalThis.fetch = fakeUpstream(new Response("{}"));
		const req = new Request("https://shim.test/v1/chat/completions", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
		const res = await worker.fetch(req, env);
		expect(res.status).toBe(401);
	});

	it("fails closed with 401 when SHIM_TOKEN is unset (misconfigured deploy)", async () => {
		globalThis.fetch = fakeUpstream(new Response("{}"));
		const req = shimRequest({});
		const res = await worker.fetch(req, { ...env, SHIM_TOKEN: undefined });
		expect(res.status).toBe(401);
	});

	it("fails closed with 401 on a wrong token", async () => {
		globalThis.fetch = fakeUpstream(new Response("{}"));
		const req = shimRequest({}, { "x-shim-token": "wrong" });
		const res = await worker.fetch(req, env);
		expect(res.status).toBe(401);
	});

	it("forwards an upstream JSON completion unchanged and hits env.UPSTREAM", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify(completion()), { status: 200, headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash", messages: [] }), env);
		expect(res.status).toBe(200);
		expect(captured.url).toBe(UPSTREAM);
		const body = await res.json();
		expect(body.choices[0].message.content).toBe("ok");
	});

	it("forwards the caller's authorization (BYOK key) upstream and never the shim token", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify(completion()), { headers: { "content-type": "application/json" } }));
		await worker.fetch(shimRequest({ model: "m" }, { authorization: "Bearer byok-key" }), env);
		expect(captured.headers.get("authorization")).toBe("Bearer byok-key");
		expect(captured.headers.get("x-shim-token")).toBe(null);
	});

	it("forwards only allowlisted headers upstream", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify(completion()), { headers: { "content-type": "application/json" } }));
		await worker.fetch(shimRequest({ model: "m" }, { "x-secret": "nope", accept: "text/event-stream" }), env);
		expect(captured.headers.get("x-secret")).toBe(null);
		expect(captured.headers.get("accept")).toBe("text/event-stream");
		expect(captured.headers.get("host")).toBe(null);
	});

	it("remaps a choices-less error body (z.ai auth/quota style) to 502 so the route cascade fires", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify({ code: 1113, msg: "Insufficient Balance" }), { status: 200, headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(502);
	});

	it("remaps a 200 with an empty body to 502 so the cascade fires", async () => {
		globalThis.fetch = fakeUpstream(new Response("", { status: 200, headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(502);
	});

	it("does NOT remap a completion that merely carries a numeric code field", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify({ ...completion(), code: 200 }), { headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(200);
	});

	it("streams SSE responses through, including the [DONE] terminator", async () => {
		globalThis.fetch = fakeUpstream(sseResponse([
			JSON.stringify({ choices: [{ delta: { reasoning_content: "th" } }] }),
			JSON.stringify({ choices: [{ delta: { content: "ok" }, finish_reason: "stop" }] }),
		]));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(200);
		const text = await res.text();
		expect(text).toContain('"reasoning_content"');
		expect(text).toContain("[DONE]");
	});

	it("remaps a leading SSE error event to 502 so the cascade fires", async () => {
		globalThis.fetch = fakeUpstream(new Response('data: {"error":{"code":"1113","message":"Insufficient Balance"}}\n\n', { status: 200, headers: { "content-type": "text/event-stream" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(502);
	});

	it("aborts a hung upstream and returns 502 so the cascade fires", async () => {
		globalThis.fetch = (url, init) => new Promise((_, reject) => {
			init.signal.addEventListener("abort", () => reject(new DOMException("The operation was aborted", "AbortError")));
		});
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), { ...env, UPSTREAM_TIMEOUT_MS: "50" });
		expect(res.status).toBe(502);
		const body = await res.json();
		expect(body.error.message).toContain("upstream_timeout");
	});

	it("remaps a leading SSE error event to 502 even when split across transport chunks", async () => {
		const encoder = new TextEncoder();
		let sink;
		const body = new ReadableStream({ start(c) { sink = c; } });
		globalThis.fetch = fakeUpstream(new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } }));
		const resPromise = worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		sink.enqueue(encoder.encode('data: {"err'));
		sink.enqueue(encoder.encode('or":{"code":"1113"}}\n\ndata: [DONE]\n\n'));
		sink.close();
		const res = await resPromise;
		expect(res.status).toBe(502);
	});

	it("remaps a 200 with an empty choices array to 502 so the cascade fires", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify({ choices: [] }), { status: 200, headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(502);
	});

	it("remaps a 200 with an unparseable JSON body to 502 so the cascade fires", async () => {
		globalThis.fetch = fakeUpstream(new Response("not json at all", { status: 200, headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(502);
	});

	it("drops content-length/content-encoding when re-serving a decoded JSON body", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify(completion()), {
			status: 200,
			headers: { "content-type": "application/json", "content-encoding": "gzip", "content-length": "999" },
		}));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		expect(res.status).toBe(200);
		expect(res.headers.get("content-encoding")).toBe(null);
		expect(res.headers.get("content-length")).not.toBe("999");
	});

	it("ignores a non-numeric UPSTREAM_TIMEOUT_MS instead of aborting every request instantly", async () => {
		globalThis.fetch = fakeUpstream(new Response(JSON.stringify(completion()), { status: 200, headers: { "content-type": "application/json" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), { ...env, UPSTREAM_TIMEOUT_MS: "soon" });
		expect(res.status).toBe(200);
	});

	it("aborts the upstream when the client cancels the stream", async () => {
		const encoder = new TextEncoder();
		let upstreamController;
		const body = new ReadableStream({
			start(c) {
				upstreamController = c;
				c.enqueue(encoder.encode('data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'));
				// never closes — a live generation stream
			},
		});
		globalThis.fetch = fakeUpstream(new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } }));
		const res = await worker.fetch(shimRequest({ model: "glm-5.3-flash" }), env);
		const reader = res.body.getReader();
		await reader.read();
		await reader.cancel();
		await new Promise((resolve) => setTimeout(resolve, 10));
		expect(captured.signal.aborted).toBe(true);
	});
});
