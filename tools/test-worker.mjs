// Quick checks for the download counters in src/worker.js, with a fake GitHub, cache and D1.   node tools/test-worker.mjs
import assert from "node:assert/strict";

const store = new Map();
globalThis.caches = { default: {
  async match(req) { const v = store.get(req.url); return v ? new Response(v) : undefined; },
  async put(req, res) { store.set(req.url, await res.text()); },
} };
const INSTALLER = new Uint8Array([1, 2, 3, 4]);
let githubCalls = 0, installerCalls = 0, githubDown = false;
const sha = [...new Uint8Array(await crypto.subtle.digest("SHA-256", INSTALLER))].map((b) => b.toString(16).padStart(2, "0")).join("");
globalThis.fetch = async (u) => {
  u = String(u);
  if (u.includes("/releases/latest")) {
    return Response.json({ tag_name: "v9.9.9", published_at: "2026-01-01T00:00:00Z", assets: [{ name: "ShabpaSetup.exe", size: 4, digest: "sha256:" + sha, browser_download_url: "https://github.com/MrPitPot/shabpa/releases/download/v9.9.9/ShabpaSetup.exe" }] });
  }
  if (u.includes("/releases?per_page=100")) {
    githubCalls++;
    if (githubDown) return new Response("rate limited", { status: 403 });
    return Response.json([
      { assets: [{ name: "ShabpaSetup.exe", download_count: 100 }, { name: "ShabpaSetup.exe.sha256", download_count: 55 }, { name: "latest.json", download_count: 9 }] },
      { assets: [{ name: "ShabpaSetup.exe", download_count: 20 }] },
    ]);
  }
  if (u.includes("/download/v9.9.9/ShabpaSetup.exe")) { installerCalls++; return new Response(INSTALLER); }
  throw new Error("unexpected fetch " + u);
};
const db = { rows: {}, prepare(sql) { return { _k: null, _v: null, bind(k, v) { this._k = k; this._v = v; return this; },
  async run() { if (sql.includes("'gh_total'")) { db.rows.gh_total = Math.max(db.rows.gh_total || 0, this._k); return; } db.rows[this._k] = (db.rows[this._k] || 0) + 1; },
  async all() { return { results: Object.entries(db.rows).map(([k, n]) => ({ k, n })) }; } }; } };

const { default: worker } = await import("../src/worker.js");
const waits = [];
const ctx = { waitUntil: (p) => waits.push(p) };
const call = async (path, env, headers = {}) => { const r = await worker.fetch(new Request("https://shabpa.ir" + path, { headers }), env, ctx); await Promise.all(waits.splice(0)); return r; };

// no DB: only GitHub, only installer assets are summed
let r = await (await call("/api/stats", {})).json();
assert.equal(r.github, 120); assert.equal(r.site, null); assert.equal(r.total, 120);

// downloads from the site are counted, bots and ranges are not
const env = { DB: db };
await call("/download/ShabpaSetup.exe", env, { "User-Agent": "Mozilla/5.0 Chrome/120" });
await call("/download/ShabpaSetup.exe", env, { "User-Agent": "Mozilla/5.0 Chrome/120" });
await call("/download/ShabpaSetup.exe", env, { "User-Agent": "Googlebot/2.1" });
await call("/download/ShabpaSetup.exe", env, { "User-Agent": "Mozilla/5.0", Range: "bytes=2-3" });
assert.equal(db.rows.site_downloads, 2);
assert.equal(db.rows.proxy_fills, 1, "only the first request filled the cache from GitHub");
assert.equal(installerCalls, 1);

// the cache fill is taken off the total: 120 (GitHub) + 2 (site) - 1 (fill)
store.delete("https://shabpa.ir/__cache/gh-downloads");
r = await (await call("/api/stats", env)).json();
assert.deepEqual([r.github, r.site, r.total], [120, 2, 121]);
assert.equal((await call("/api/stats", env)).headers.get("Cache-Control"), "public, max-age=300");
assert.equal((await call("/api/stats", env, {})).status, 200);
assert.equal((await worker.fetch(new Request("https://shabpa.ir/api/stats", { method: "POST" }), env, ctx)).status, 405);
// GitHub refuses (rate limit): the last stored total keeps the number on screen and nothing goes backwards
githubDown = true;
store.delete("https://shabpa.ir/__cache/gh-downloads");
r = await (await call("/api/stats", env)).json();
assert.deepEqual([r.github, r.site, r.total], [120, 2, 121], "falls back to the stored GitHub total");
const calls = githubCalls;
await call("/api/stats", env);
assert.equal(githubCalls, calls, "after a refusal it does not ask GitHub again straight away");
// a brand-new database with GitHub down: no number rather than a wrong one
db.rows = {}; store.clear();
r = await (await call("/api/stats", env)).json();
assert.equal(r.total, null);
console.log("worker counters: ok");

/* ---------- ratings ---------- */
const rdb = {
  ratings: new Map(), limits: new Map(), sawIp: false,
  prepare(sql) {
    const q = { args: [], bind(...a) { this.args = a; return this; },
      async run() {
        if (sql.startsWith("INSERT INTO rate_limits")) { const [k, hour] = this.args; const o = rdb.limits.get(k); rdb.limits.set(k, { n: (o ? o.n : 0) + 1, hour }); }
        else if (sql.startsWith("DELETE FROM rate_limits")) { for (const [k, v] of rdb.limits) if (v.hour < this.args[0]) rdb.limits.delete(k); }
        else if (sql.startsWith("INSERT INTO ratings")) {
          const [id, stars, version, lang, day] = this.args; const o = rdb.ratings.get(id);
          rdb.ratings.set(id, { stars, version, lang, created: o ? o.created : day, updated: day });
        } else throw new Error("unexpected run " + sql);
      },
      async first() { const o = rdb.limits.get(this.args[0]); return o ? { n: o.n } : null; },
      async all() {
        if (!sql.includes("FROM ratings")) throw new Error("unexpected all " + sql);
        const c = {}; for (const r of rdb.ratings.values()) c[r.stars] = (c[r.stars] || 0) + 1;
        return { results: Object.entries(c).map(([stars, n]) => ({ stars: Number(stars), c: n })) };
      } };
    return q;
  } };
const renv = { DB: rdb, RATE_SALT: "test-salt" };
const vote = async (body, { ip = "203.0.113.7", type = "application/json", method = "POST" } = {}) => {
  const r = await worker.fetch(new Request("https://shabpa.ir/api/rate", { method, headers: { "Content-Type": type, "CF-Connecting-IP": ip, "User-Agent": "Shabpa/9.9.9" }, body: method === "POST" ? (typeof body === "string" ? body : JSON.stringify(body)) : undefined }), renv, ctx);
  await Promise.all(waits.splice(0)); return r;
};
const ok = (n) => ({ stars: n, id: "0123456789abcdef0123456789abcdef", version: "3.16.0", lang: "fa" });
const summary = async () => { store.delete("https://shabpa.ir/__cache/ratings"); const r = await worker.fetch(new Request("https://shabpa.ir/api/ratings"), renv, ctx); await Promise.all(waits.splice(0)); return r; };

// a valid vote is stored, and the same install changing its mind replaces it
assert.deepEqual(await (await vote(ok(5))).json(), { ok: true });
assert.equal(rdb.ratings.size, 1);
await vote(ok(2));
assert.equal(rdb.ratings.size, 1, "one vote per install");
assert.equal([...rdb.ratings.values()][0].stars, 2);
// nothing stored contains the id, the address or the user agent
const rows = JSON.stringify([...rdb.ratings.entries(), ...rdb.limits.entries()]);
assert.ok(!rows.includes("0123456789abcdef0123456789abcdef"), "the raw install id is never stored");
assert.ok(!rows.includes("203.0.113.7") && !rows.includes("Shabpa/9.9.9"), "no IP address and no user agent is stored");
assert.ok([...rdb.limits.keys()].every((k) => k.startsWith("all:") || /^ip:[0-9a-f]{64}$/.test(k)), "the flood counter is keyed by a hash");

// bad input is refused with a plain error
for (const bad of [{ ...ok(5), stars: 0 }, { ...ok(5), stars: 6 }, { ...ok(5), stars: 4.5 }, { ...ok(5), stars: "5" }, { ...ok(5), id: "short" }, { ...ok(5), id: "G".repeat(32) },
  { ...ok(5), version: "3.16" }, { ...ok(5), version: "3.16.0-beta" }, { ...ok(5), lang: "de" }, [1, 2], "not json", null, {}])
  assert.equal((await vote(typeof bad === "string" ? bad : bad)).status, 400, JSON.stringify(bad));
assert.equal((await vote(ok(5), { type: "text/plain" })).status, 415);
assert.equal((await vote("x".repeat(2000))).status, 413);
assert.equal((await vote(ok(5), { method: "GET" })).status, 405);
assert.equal((await worker.fetch(new Request("https://shabpa.ir/api/rate", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }), {}, ctx)).status, 503, "without a database it says so");
assert.equal(rdb.ratings.size, 1, "bad requests stored nothing");

// a flood from one address is stopped after 20 an hour, another address is not affected
let last;
for (let i = 0; i < 25; i++) last = await vote({ ...ok(4), id: i.toString(16).padStart(32, "0") }, { ip: "198.51.100.9" });
assert.equal(last.status, 429);
assert.equal((await vote({ ...ok(4), id: "f".repeat(32) }, { ip: "198.51.100.10" })).status, 200);

// the summary is read back honestly
rdb.ratings.clear(); rdb.limits.clear();
for (let i = 0; i < 4; i++) await vote({ ...ok(i < 3 ? 5 : 4), id: (i + 1).toString(16).padStart(32, "0") }, { ip: "192.0.2." + i });
let sum = await (await summary()).json();
assert.deepEqual(sum, { count: 4, average: 4.8, distribution: [0, 0, 0, 1, 3] });
assert.equal((await summary()).headers.get("Cache-Control"), "public, max-age=300");
assert.equal((await worker.fetch(new Request("https://shabpa.ir/api/ratings", { method: "POST" }), renv, ctx)).status, 405);

// the home page gets aggregateRating only from 10 real votes (a small stand-in for Cloudflare's HTMLRewriter)
globalThis.HTMLRewriter = class { constructor() { this.h = null; } on(_s, h) { this.h = h; return this; }
  transform(res) { const h = this.h; return { text: () => res.text().then((t) => t.replace(/(<script type="application\/ld\+json">)([\s\S]*?)(<\/script>)/, (_m, a, b, c) => { let out = b; h.text({ text: b, lastInTextNode: true, remove() {}, replace(x) { out = x; } }); return a + out + c; })) }; } };
const page = '<html><script type="application/ld+json">{"@graph":[{"@type":"SoftwareApplication","name":"x"}]}</script></html>';
const home = async () => { store.delete("https://shabpa.ir/__cache/ratings"); const r = await worker.fetch(new Request("https://shabpa.ir/"), { ...renv, ASSETS: { fetch: async () => new Response(page, { headers: { "Content-Type": "text/html" } }) } }, ctx); await Promise.all(waits.splice(0)); return r.text(); };
assert.ok(!(await home()).includes("aggregateRating"), "4 votes: no rating in the structured data");
for (let i = 0; i < 8; i++) await vote({ ...ok(5), id: (i + 20).toString(16).padStart(32, "0") }, { ip: "192.0.2." + (i + 20) });
const html = await home();
assert.ok(html.includes('"aggregateRating"') && html.includes('"ratingCount":12') && html.includes('"ratingValue":4.9'), html);
console.log("worker ratings: ok");
