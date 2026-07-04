type StoredResponse = {
  ts: number;
  status: number;
  statusText: string;
  headers: Array<[string, string]>;
  body: ArrayBuffer;
};

const DEFAULT_TTL_MS = 45_000;
const DEFAULT_MAX_ENTRIES = 64;

const responseCache = new Map<string, StoredResponse>();
const inflight = new Map<string, Promise<Response>>();

function envNumber(name: string, fallback: number): number {
  const raw = typeof process !== "undefined" && process.env ? process.env[name] : undefined;
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isEnabled(): boolean {
  const raw = typeof process !== "undefined" && process.env ? process.env.NEXT_PUBLIC_GROUGAL_FETCH_CACHE : undefined;
  return raw == null || !["0", "false", "no", "off"].includes(raw.toLowerCase());
}

function shouldCache(input: RequestInfo | URL, init?: RequestInit): boolean {
  if (!isEnabled()) return false;
  const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
  if (method !== "POST") return false;
  if (!init?.body && !(input instanceof Request && input.body)) return false;

  const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const lowered = url.toLowerCase();
  if (!lowered.includes("/api/")) return false;

  return ["analyze", "analyse", "arena", "solve", "solver", "recommend", "recommendation", "action", "capture", "recognition"]
    .some((keyword) => lowered.includes(keyword));
}

function prune(): void {
  const maxEntries = envNumber("NEXT_PUBLIC_GROUGAL_FETCH_CACHE_ENTRIES", DEFAULT_MAX_ENTRIES);
  while (responseCache.size > maxEntries) {
    const first = responseCache.keys().next().value;
    if (!first) break;
    responseCache.delete(first);
  }
}

async function bodyToString(body: BodyInit | null | undefined): Promise<string> {
  if (body == null) return "";
  if (typeof body === "string") return body;
  if (body instanceof URLSearchParams) return body.toString();
  if (body instanceof Blob) return await body.text();
  if (body instanceof FormData) {
    const pairs: string[] = [];
    body.forEach((value, key) => {
      if (typeof value === "string") {
        pairs.push(`${key}=${value}`);
      } else {
        pairs.push(`${key}=${value.name}:${value.size}`);
      }
    });
    return pairs.sort().join("&");
  }
  if (body instanceof ArrayBuffer) return Array.from(new Uint8Array(body)).join(",");
  if (ArrayBuffer.isView(body)) return Array.from(new Uint8Array(body.buffer)).join(",");
  return String(body);
}

async function stableKey(input: RequestInfo | URL, init?: RequestInit): Promise<string> {
  const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
  const raw = `${method}\n${url}\n${await bodyToString(init?.body ?? null)}`;

  if (typeof crypto !== "undefined" && crypto.subtle) {
    const encoded = new TextEncoder().encode(raw);
    const digest = await crypto.subtle.digest("SHA-256", encoded);
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  let hash = 2166136261;
  for (let i = 0; i < raw.length; i += 1) {
    hash ^= raw.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return String(hash >>> 0);
}

function responseFromStored(entry: StoredResponse, cacheState: string): Response {
  const headers = new Headers(entry.headers);
  headers.set("X-Grougal-Frontend-Cache", cacheState);
  return new Response(entry.body.slice(0), { status: entry.status, statusText: entry.statusText, headers });
}

export async function perfFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (!shouldCache(input, init)) return fetch(input, init);

  const ttlMs = envNumber("NEXT_PUBLIC_GROUGAL_FETCH_CACHE_TTL_MS", DEFAULT_TTL_MS);
  const key = await stableKey(input, init);
  const now = Date.now();
  const cached = responseCache.get(key);
  if (cached && now - cached.ts <= ttlMs) return responseFromStored(cached, "HIT");

  const running = inflight.get(key);
  if (running) return (await running).clone();

  const request = fetch(input, init).then(async (response) => {
    if (!response.ok) return response;
    const body = await response.clone().arrayBuffer();
    responseCache.set(key, {
      ts: Date.now(),
      status: response.status,
      statusText: response.statusText,
      headers: Array.from(response.headers.entries()),
      body,
    });
    prune();
    return response;
  });

  inflight.set(key, request);
  try {
    return await request;
  } finally {
    inflight.delete(key);
  }
}


export async function perfFetchWithRetry(input: RequestInfo | URL, init?: RequestInit, retries = 2): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await perfFetch(input, init);
      if (res.ok) return res;
      lastError = new Error(`HTTP ${res.status}`);
    } catch (e) {
      lastError = e;
    }
    if (attempt < retries) {
      await new Promise((r) => setTimeout(r, 250 * (attempt + 1)));
    }
  }
  throw lastError instanceof Error ? lastError : new Error('Unknown fetch error');
}
