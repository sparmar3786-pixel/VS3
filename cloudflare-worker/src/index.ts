export interface Env {
  BACKEND_ORIGIN: string;
  ASSETS: Fetcher;
  EDGE_API_KEY?: string;
}

const PUBLIC = new Set(["/health", "/api/config", "/api/indices", "/api/strategies", "/api/ai/layers"]);

function cors(origin: string | null) {
  const h = new Headers();
  h.set("Access-Control-Allow-Origin", origin || "*");
  h.set("Access-Control-Allow-Headers", "content-type, x-app-key, authorization");
  h.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  h.set("Vary", "Origin");
  return h;
}

function target(env: Env, request: Request) {
  const incoming = new URL(request.url);
  const base = env.BACKEND_ORIGIN.replace(/\/$/, "");
  return new Request(base + incoming.pathname + incoming.search, request);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") return new Response(null, { headers: cors(request.headers.get("Origin")) });

    const url = new URL(request.url);

    if (!url.pathname.startsWith("/api/") && url.pathname !== "/health" && url.pathname !== "/ws") {
      const asset = await env.ASSETS.fetch(request);
      if (asset.status !== 404) return asset;
    }

    if (url.pathname === "/health") {
      return Response.json({ status: "edge-ok", service: "vandana2-edge" }, { headers: cors(request.headers.get("Origin")) });
    }

    if (url.pathname === "/ws") return fetch(target(env, request));

    if (url.pathname.startsWith("/api/")) {
      if (env.EDGE_API_KEY && !PUBLIC.has(url.pathname) &&
          request.headers.get("x-app-key") !== env.EDGE_API_KEY) {
        return Response.json({ error: "unauthorized" }, { status: 401, headers: cors(request.headers.get("Origin")) });
      }
      const response = await fetch(target(env, request));
      const headers = new Headers(response.headers);
      cors(request.headers.get("Origin")).forEach((v, k) => headers.set(k, v));
      return new Response(response.body, { status: response.status, headers });
    }

    return new Response("Not found", { status: 404 });
  },
};
