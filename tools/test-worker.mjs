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
