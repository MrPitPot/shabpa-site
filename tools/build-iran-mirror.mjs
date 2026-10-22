// Builds a self-contained static copy of the site that can be uploaded to any web host
// (for example a host inside Iran, where Cloudflare / foreign sites are often filtered).
//
//   node tools/build-iran-mirror.mjs [outDir]        (default: dist-iran)
//
// It copies public/, downloads the latest Shabpa installer from the official GitHub release,
// verifies its SHA-256 against the digest GitHub publishes, and writes:
//   <out>/download/ShabpaSetup.exe     the installer, served from your own host
//   <out>/api/latest                   release info in the same JSON the Cloudflare Worker serves
// No dependencies; needs Node 18+.

import { createHash } from "node:crypto";
import { cp, mkdir, rm, writeFile, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const REPO = "MrPitPot/shabpa";
const FILE = "ShabpaSetup.exe";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.resolve(process.argv[2] || path.join(root, "dist-iran"));

const rel = await (await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, {
  headers: { Accept: "application/vnd.github+json", "User-Agent": "shabpa-site-mirror" },
})).json();
const asset = (rel.assets || []).find((a) => a.name === FILE);
const digest = /^sha256:([0-9a-f]{64})$/i.exec((asset && asset.digest) || "");
if (!asset || !digest || !/^v\d+\.\d+\.\d+$/.test(rel.tag_name)) throw new Error("Unexpected release data from GitHub");

console.log(`Downloading ${rel.tag_name} (${(asset.size / 1048576).toFixed(1)} MB) ...`);
const buf = Buffer.from(await (await fetch(asset.browser_download_url, { headers: { "User-Agent": "shabpa-site-mirror" } })).arrayBuffer());
const sha = createHash("sha256").update(buf).digest("hex");
if (sha !== digest[1].toLowerCase() || buf.length !== asset.size) throw new Error(`Checksum mismatch: got ${sha}, GitHub says ${digest[1]}`);
console.log("SHA-256 verified:", sha);

await rm(out, { recursive: true, force: true });
await cp(path.join(root, "public"), out, { recursive: true });
await mkdir(path.join(out, "download"), { recursive: true });
await mkdir(path.join(out, "api"), { recursive: true });
await writeFile(path.join(out, "download", FILE), buf);
await writeFile(path.join(out, "api", "latest"), JSON.stringify({
  version: rel.tag_name.slice(1), published: rel.published_at, file: FILE, size: asset.size, sha256: sha,
  github: asset.browser_download_url, url: `/download/${FILE}`,
}));

// the Cloudflare-only file becomes a plain-text reference for configuring the new host
const headers = await readFile(path.join(out, "_headers"), "utf8");
await rm(path.join(out, "_headers"));
await writeFile(path.join(out, "HOST-HEADERS.txt"),
  "Security headers the site was designed to be served with (translate to your web server's syntax).\n" +
  "Also: serve /api/latest with Content-Type application/json, redirect http->https and www->bare domain.\n\n" + headers);

console.log(`Done. Upload the contents of: ${out}`);
