// Shabpa site worker.
//  - forces https and the bare domain
//  - GET /api/latest              latest release info (from GitHub, cached at the edge)
//  - GET /download/ShabpaSetup.exe  the installer, served from our own domain so visitors whose
//                                   network is slow or blocked towards GitHub can still get it.
//    The file is fetched from the official GitHub release, its SHA-256 is checked against the
//    digest GitHub publishes, and only then is it cached. If anything does not match we send the
//    visitor to GitHub instead of serving the file.
// Everything else is handed to the static assets.

const CANONICAL_HOST = "shabpa.ir";
const REPO = "MrPitPot/shabpa";
const FILE = "ShabpaSetup.exe";
const RELEASE_API = `https://api.github.com/repos/${REPO}/releases/latest`;
const ASSET_URL = new RegExp(`^https://github\\.com/${REPO}/releases/download/v\\d+\\.\\d+\\.\\d+/${FILE.replace(".", "\\.")}$`);

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Cross-Origin-Resource-Policy": "same-origin",
  "Strict-Transport-Security": "max-age=31536000",
};

function json(body, status, cacheControl) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": cacheControl, ...SECURITY_HEADERS },
  });
}

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

/** Latest release info. Fresh copy for 10 minutes, and a day-long stale copy in case GitHub is unreachable. */
async function latestInfo(ctx) {
  const cache = caches.default;
  const fresh = new Request("https://shabpa.ir/__cache/latest");
  const stale = new Request("https://shabpa.ir/__cache/latest-stale");
  const hit = await cache.match(fresh);
  if (hit) return hit.json();
  try {
    const r = await fetch(RELEASE_API, { headers: { Accept: "application/vnd.github+json", "User-Agent": "shabpa-site" } });
    if (!r.ok) throw new Error("github " + r.status);
    const d = await r.json();
    const a = (d.assets || []).find((x) => x && x.name === FILE);
    const m = /^sha256:([0-9a-f]{64})$/i.exec((a && a.digest) || "");
    if (!a || !m || !/^v\d+\.\d+\.\d+$/.test(d.tag_name) || !ASSET_URL.test(a.browser_download_url)) throw new Error("unexpected release shape");
    const info = {
      version: d.tag_name.slice(1),
      published: d.published_at,
      file: FILE,
      size: a.size,
      sha256: m[1].toLowerCase(),
      github: a.browser_download_url,
      url: `/download/${FILE}`,
    };
    const body = JSON.stringify(info);
    ctx.waitUntil(Promise.all([
      cache.put(fresh, new Response(body, { headers: { "Cache-Control": "max-age=600" } })),
      cache.put(stale, new Response(body, { headers: { "Cache-Control": "max-age=86400" } })),
    ]));
    return info;
  } catch (e) {
    const old = await cache.match(stale);
    if (old) return old.json();
    throw e;
  }
}

function parseRange(header, size) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(header || "");
  if (!m || (m[1] === "" && m[2] === "")) return null;
  let start, end;
  if (m[1] === "") { start = Math.max(0, size - Number(m[2])); end = size - 1; }
  else { start = Number(m[1]); end = m[2] === "" ? size - 1 : Math.min(Number(m[2]), size - 1); }
  return start <= end && start < size ? { start, end } : "bad";
}

async function installer(request, ctx, info) {
  const cache = caches.default;
  const key = new Request(`https://shabpa.ir/__cache/installer/${info.sha256}`);
  const base = {
    "Content-Type": "application/octet-stream",
    "Content-Disposition": `attachment; filename="${FILE}"`,
    "Accept-Ranges": "bytes",
    "Cache-Control": "public, max-age=3600",
    ETag: `"${info.sha256}"`,
    ...SECURITY_HEADERS,
  };
  const rangeHeader = request.headers.get("Range");
  const hit = await cache.match(key);

  /* Cached copy, whole file: stream it straight through (no copying, almost no CPU) */
  if (hit && !rangeHeader) {
    return new Response(request.method === "HEAD" ? null : hit.body, { status: 200, headers: { ...base, "Content-Length": String(info.size) } });
  }

  let buf;
  if (hit) buf = await hit.arrayBuffer();
  else {
    const up = await fetch(info.github, { redirect: "follow", headers: { "User-Agent": "shabpa-site" } });
    if (!up.ok) return Response.redirect(info.github, 302);
    buf = await up.arrayBuffer();
    if (hex(await crypto.subtle.digest("SHA-256", buf)) !== info.sha256 || buf.byteLength !== info.size) return Response.redirect(info.github, 302);
    ctx.waitUntil(cache.put(key, new Response(buf, { headers: { "Cache-Control": "max-age=86400" } })));
  }
  const range = parseRange(rangeHeader, buf.byteLength);
  if (range === "bad") return new Response(null, { status: 416, headers: { ...base, "Content-Range": `bytes */${buf.byteLength}` } });
  if (range) return new Response(request.method === "HEAD" ? null : buf.slice(range.start, range.end + 1), { status: 206, headers: { ...base, "Content-Range": `bytes ${range.start}-${range.end}/${buf.byteLength}`, "Content-Length": String(range.end - range.start + 1) } });
  return new Response(request.method === "HEAD" ? null : buf, { status: 200, headers: { ...base, "Content-Length": String(buf.byteLength) } });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const isDev = env.DEV === "1"; /* only set by `wrangler dev --var DEV:1` */
    const host = url.hostname;
    const onWorkersDev = host.endsWith(".workers.dev"); /* second entry point that does not use our domain name */
    if (!isDev) {
      if (host === "www." + CANONICAL_HOST) { url.protocol = "https:"; url.hostname = CANONICAL_HOST; url.port = ""; return Response.redirect(url.toString(), 301); }
      if (url.protocol === "http:") { url.protocol = "https:"; url.port = ""; return Response.redirect(url.toString(), 301); }
      if (host !== CANONICAL_HOST && !onWorkersDev) { url.hostname = CANONICAL_HOST; url.port = ""; return Response.redirect(url.toString(), 301); }
    }
    const country = (request.cf && request.cf.country) || "??";

    if (url.pathname === "/api/latest" || url.pathname === `/download/${FILE}`) {
      if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
      try {
        const info = await latestInfo(ctx);
        if (url.pathname === "/api/latest") return json(info, 200, "public, max-age=300");
        const range = request.headers.get("Range");
        if (request.method === "GET" && (!range || /^bytes=0-/.test(range))) console.log(JSON.stringify({ evt: "download", v: info.version, c: country }));
        return await installer(request, ctx, info);
      } catch (e) {
        if (url.pathname === "/api/latest") return json({ error: "unavailable" }, 502, "no-store");
        return Response.redirect(`https://github.com/${REPO}/releases/latest`, 302);
      }
    }

    if ((url.pathname === "/" || url.pathname === "/en/") && request.method === "GET") {
      console.log(JSON.stringify({ evt: "view", p: url.pathname, c: country }));
    }
    const res = await env.ASSETS.fetch(request);
    if (!onWorkersDev) return res;
    const out = new Response(res.body, res);
    out.headers.set("X-Robots-Tag", "noindex");
    return out;
  },
};
