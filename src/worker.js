// Shabpa site worker.
//  - forces https and the bare domain
//  - GET /api/latest              latest release info (from GitHub, cached at the edge)
//  - GET /api/stats               total installer downloads: GitHub (all releases, which also covers winget, because the
//                                 winget manifest points at the GitHub asset) plus the downloads served from this site
//  - GET /download/ShabpaSetup.exe  the installer, served from our own domain so visitors whose
//                                   network is slow or blocked towards GitHub can still get it.
//    The file is fetched from the official GitHub release, its SHA-256 is checked against the
//    digest GitHub publishes, and only then is it cached. If anything does not match we send the
//    visitor to GitHub instead of serving the file.
//  - POST /api/rate               a star rating (1-5) sent by the app when the person agrees; one vote per install, a second vote replaces the first
//  - GET /api/ratings             {count, average, distribution}; the home pages show it from 5 votes, the structured data gets it from 10
// Everything else is handed to the static assets.

const CANONICAL_HOST = "shabpa.ir";
const REPO = "MrPitPot/shabpa";
const FILE = "ShabpaSetup.exe";
const RELEASE_API = `https://api.github.com/repos/${REPO}/releases/latest`;
const ASSET_URL = new RegExp(`^https://github\\.com/${REPO}/releases/download/v\\d+\\.\\d+\\.\\d+/${FILE.replace(".", "\\.")}$`);

const BOT_UA = /bot|crawl|spider|slurp|preview|headless|curl|wget|python|monitor|uptime|check/i;
const RELEASES_API = `https://api.github.com/repos/${REPO}/releases?per_page=100`;

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

/* Counters live in D1 (binding DB, table counters). Without the binding everything below quietly does nothing. */
async function bump(env, key) {
  if (!env.DB) return;
  try { await env.DB.prepare("INSERT INTO counters (k, n) VALUES (?1, 1) ON CONFLICT(k) DO UPDATE SET n = n + 1").bind(key).run(); } catch (e) { /* counting must never break a download */ }
}

async function readCounters(env) {
  const out = { site: 0, fills: 0, gh: null, enabled: !!env.DB };
  if (!env.DB) return out;
  try {
    const { results } = await env.DB.prepare("SELECT k, n FROM counters WHERE k IN ('site_downloads', 'proxy_fills', 'gh_total')").all();
    for (const r of results || []) {
      if (r.k === "site_downloads") out.site = r.n | 0;
      else if (r.k === "proxy_fills") out.fills = r.n | 0;
      else if (r.k === "gh_total") out.gh = r.n | 0;
    }
  } catch (e) { out.enabled = false; }
  return out;
}

/* The last good GitHub total is kept in D1 and only ever goes up (GitHub's own count never decreases), so a failed refresh cannot hide the number or move it backwards. */
async function rememberGithub(env, n) {
  if (!env.DB) return;
  try { await env.DB.prepare("INSERT INTO counters (k, n) VALUES ('gh_total', ?1) ON CONFLICT(k) DO UPDATE SET n = MAX(n, excluded.n)").bind(n).run(); } catch (e) { /* ignore */ }
}

/** Sum of download_count over every release's installer asset. Fresh for 10 minutes; if GitHub refuses (rate limit) the last stored total is used. */
async function githubDownloads(ctx, env, remembered) {
  const cache = caches.default;
  const fresh = new Request("https://shabpa.ir/__cache/gh-downloads");
  const failed = new Request("https://shabpa.ir/__cache/gh-downloads-failed");
  const hit = await cache.match(fresh);
  if (hit) return (await hit.json()).n;
  if (await cache.match(failed)) return remembered; /* GitHub just refused us: do not ask again for 2 minutes */
  try {
    const headers = { Accept: "application/vnd.github+json", "User-Agent": "shabpa-site" };
    if (env.GITHUB_TOKEN) headers.Authorization = `Bearer ${env.GITHUB_TOKEN}`; /* optional secret: lifts the 60-requests-an-hour limit */
    let n = 0;
    for (let page = 1; page <= 5; page++) {
      const r = await fetch(`${RELEASES_API}&page=${page}`, { headers });
      if (!r.ok) throw new Error("github " + r.status);
      const list = await r.json();
      if (!Array.isArray(list)) throw new Error("unexpected shape");
      for (const rel of list) for (const a of rel.assets || []) if (a && a.name === FILE && Number.isFinite(a.download_count)) n += a.download_count;
      if (list.length < 100) break;
    }
    ctx.waitUntil(Promise.all([
      cache.put(fresh, new Response(JSON.stringify({ n }), { headers: { "Cache-Control": "max-age=600" } })),
      rememberGithub(env, n),
    ]));
    return Math.max(n, remembered || 0);
  } catch (e) {
    console.log(JSON.stringify({ evt: "github-stats-failed", err: String(e && e.message || e) }));
    ctx.waitUntil(cache.put(failed, new Response("1", { headers: { "Cache-Control": "max-age=120" } })));
    return remembered;
  }
}

async function stats(ctx, env) {
  const c = await readCounters(env);
  const github = await githubDownloads(ctx, env, c.gh);
  /* The site copies the installer from GitHub only when its own cache is empty; that one GitHub download is not a visitor, so it is taken off. */
  const total = github === null ? null : Math.max(0, github + c.site - c.fills);
  return { github, site: c.enabled ? c.site : null, total, updated: new Date().toISOString() };
}

/* ---------- ratings ----------
   The app sends {stars, version, lang, id} only after the person said yes. The id is a random install id; only its SHA-256 is stored, so nobody can read an id back and
   a second vote from the same install replaces the first. No IP address and no user agent is ever stored: the flood counter is keyed by an HMAC of IP and hour. */
const RATE_BODY_MAX = 512;
const RATE_PER_HOUR = 20;          /* votes one address may send per hour */
const RATE_GLOBAL_PER_HOUR = 600;  /* votes all addresses together may send per hour */

function validRating(x) {
  return !!x && typeof x === "object" && !Array.isArray(x)
    && Number.isInteger(x.stars) && x.stars >= 1 && x.stars <= 5
    && typeof x.id === "string" && /^[0-9a-f]{32}$/.test(x.id)
    && typeof x.version === "string" && /^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(x.version)
    && (x.lang === "fa" || x.lang === "en");
}

async function hmacHex(secret, text) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret || "shabpa-no-salt"), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(text)));
}

/** True while the sender is under the hourly limits. Old counters are deleted on the way. */
async function underRateLimit(env, ip) {
  const hour = Math.floor(Date.now() / 3600000);
  const mine = "ip:" + (await hmacHex(env.RATE_SALT, ip + "|" + hour));
  const run = async (k) => {
    await env.DB.prepare("INSERT INTO rate_limits (k, n, hour) VALUES (?1, 1, ?2) ON CONFLICT(k) DO UPDATE SET n = n + 1").bind(k, hour).run();
    const row = await env.DB.prepare("SELECT n FROM rate_limits WHERE k = ?1").bind(k).first();
    return row ? row.n : 1;
  };
  const a = await run(mine);
  const g = await run("all:" + hour);
  if (Math.random() < 0.05) await env.DB.prepare("DELETE FROM rate_limits WHERE hour < ?1").bind(hour - 24).run();
  return a <= RATE_PER_HOUR && g <= RATE_GLOBAL_PER_HOUR;
}

async function rate(request, env) {
  if (request.method !== "POST") return json({ error: "method" }, 405, "no-store");
  if (!env.DB) return json({ error: "unavailable" }, 503, "no-store");
  if (!/^application\/json(\s*;|$)/i.test(request.headers.get("Content-Type") || "")) return json({ error: "content-type" }, 415, "no-store");
  const declared = Number(request.headers.get("Content-Length") || 0);
  if (declared > RATE_BODY_MAX) return json({ error: "too-large" }, 413, "no-store");
  let text;
  try { text = await request.text(); } catch (e) { return json({ error: "bad-request" }, 400, "no-store"); }
  if (text.length > RATE_BODY_MAX) return json({ error: "too-large" }, 413, "no-store");
  let body;
  try { body = JSON.parse(text); } catch (e) { return json({ error: "bad-json" }, 400, "no-store"); }
  if (!validRating(body)) return json({ error: "invalid" }, 400, "no-store");
  try {
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (!(await underRateLimit(env, ip))) return json({ error: "rate-limited" }, 429, "no-store");
    const idHash = hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode("shabpa-rating:" + body.id)));
    const day = new Date().toISOString().slice(0, 10);
    await env.DB.prepare(
      "INSERT INTO ratings (id_hash, stars, app_version, lang, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?5) " +
      "ON CONFLICT(id_hash) DO UPDATE SET stars = excluded.stars, app_version = excluded.app_version, lang = excluded.lang, updated_at = excluded.updated_at"
    ).bind(idHash, body.stars, body.version, body.lang, day).run();
  } catch (e) {
    console.log(JSON.stringify({ evt: "rate-failed", err: String(e && e.message || e) }));
    return json({ error: "unavailable" }, 503, "no-store");
  }
  return json({ ok: true }, 200, "no-store");
}

/** {count, average (one decimal), distribution [1..5 stars]}, fresh for 5 minutes. null without a database. */
async function ratingSummary(ctx, env) {
  if (!env.DB) return null;
  const cache = caches.default;
  const key = new Request("https://shabpa.ir/__cache/ratings");
  const hit = await cache.match(key);
  if (hit) return hit.json();
  const { results } = await env.DB.prepare("SELECT stars, COUNT(*) AS c FROM ratings GROUP BY stars").all();
  const distribution = [0, 0, 0, 0, 0];
  for (const r of results || []) if (r.stars >= 1 && r.stars <= 5) distribution[r.stars - 1] = r.c | 0;
  const count = distribution.reduce((a, b) => a + b, 0);
  const average = count === 0 ? 0 : Math.round((distribution.reduce((a, c, i) => a + c * (i + 1), 0) / count) * 10) / 10;
  const summary = { count, average, distribution };
  ctx.waitUntil(cache.put(key, new Response(JSON.stringify(summary), { headers: { "Cache-Control": "max-age=300" } })));
  return summary;
}

/** The home pages' structured data gets aggregateRating only from 10 real votes, built from the real numbers. */
async function withAggregateRating(res, ctx, env) {
  let summary = null;
  try { summary = await ratingSummary(ctx, env); } catch (e) { return res; }
  if (!summary || summary.count < 10) return res;
  let buffer = "";
  return new HTMLRewriter().on('script[type="application/ld+json"]', {
    text(chunk) {
      buffer += chunk.text;
      if (!chunk.lastInTextNode) { chunk.remove(); return; }
      let out = buffer;
      try {
        const data = JSON.parse(buffer);
        const graph = Array.isArray(data["@graph"]) ? data["@graph"] : [data];
        for (const node of graph) if (node && node["@type"] === "SoftwareApplication")
          node.aggregateRating = { "@type": "AggregateRating", ratingValue: summary.average, ratingCount: summary.count, bestRating: 5, worstRating: 1 };
        out = JSON.stringify(data);
      } catch (e) { /* leave the original text */ }
      buffer = "";
      chunk.replace(out.replace(/</g, "\\u003c"), { html: true });
    },
  }).transform(res);
}

function parseRange(header, size) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(header || "");
  if (!m || (m[1] === "" && m[2] === "")) return null;
  let start, end;
  if (m[1] === "") { start = Math.max(0, size - Number(m[2])); end = size - 1; }
  else { start = Number(m[1]); end = m[2] === "" ? size - 1 : Math.min(Number(m[2]), size - 1); }
  return start <= end && start < size ? { start, end } : "bad";
}

async function installer(request, ctx, env, info) {
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
    ctx.waitUntil(bump(env, "proxy_fills"));
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

    if (url.pathname === "/api/stats") {
      if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
      try { return json(await stats(ctx, env), 200, "public, max-age=300"); } catch (e) { return json({ error: "unavailable" }, 502, "no-store"); }
    }

    if (url.pathname === "/api/rate") return rate(request, env);

    if (url.pathname === "/api/ratings") {
      if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
      try {
        const summary = await ratingSummary(ctx, env);
        return summary ? json(summary, 200, "public, max-age=300") : json({ error: "unavailable" }, 503, "no-store");
      } catch (e) { return json({ error: "unavailable" }, 502, "no-store"); }
    }

    if (url.pathname === "/api/latest" || url.pathname === `/download/${FILE}` || url.pathname === `/update/${FILE}`) {
      if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
      try {
        const info = await latestInfo(ctx);
        if (url.pathname === "/api/latest") return json(info, 200, "public, max-age=300");
        const range = request.headers.get("Range");
        if (request.method === "GET" && (!range || /^bytes=0-/.test(range))) {
          console.log(JSON.stringify({ evt: "download", v: info.version, c: country }));
          if (!BOT_UA.test(request.headers.get("User-Agent") || "")) ctx.waitUntil(bump(env, "site_downloads"));
        }
        return await installer(request, ctx, env, info);
      } catch (e) {
        if (url.pathname === "/api/latest") return json({ error: "unavailable" }, 502, "no-store");
        return Response.redirect(`https://github.com/${REPO}/releases/latest`, 302);
      }
    }

    if ((url.pathname === "/" || url.pathname === "/en/") && request.method === "GET") {
      console.log(JSON.stringify({ evt: "view", p: url.pathname, c: country }));
    }
    let res = await env.ASSETS.fetch(request);
    if ((url.pathname === "/" || url.pathname === "/en/") && request.method === "GET" && res.status === 200) res = await withAggregateRating(res, ctx, env);
    if (!onWorkersDev) return res;
    const out = new Response(res.body, res);
    out.headers.set("X-Robots-Tag", "noindex");
    return out;
  },
};
