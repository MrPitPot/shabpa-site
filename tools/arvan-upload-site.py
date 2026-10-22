#!/usr/bin/env python3
"""Uploads the Iran mirror (build it first:  node tools/build-iran-mirror.mjs --subpath) to the ArvanCloud bucket.

  python tools/arvan-upload-site.py [dist-iran-subpath]

Files go under the `site/` prefix ONLY (the signed updater files in `update/` are never touched), public-read, with the
right Content-Type / Cache-Control, installer first and the HTML pages last. Each file is read back over public HTTPS
and compared. Keys come from ARVAN_ACCESS_KEY / ARVAN_SECRET_KEY (process env, or the Windows user environment) and are never printed.
Settings: ARVAN_BUCKET (shabpa-dl)  ARVAN_ENDPOINT (s3.ir-central1.arvanstorage.ir)  ARVAN_REGION (ir-central1)
Standard library only."""
import datetime, hashlib, hmac, mimetypes, os, sys, urllib.error, urllib.parse, urllib.request

PREFIX = "site/"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".webp": "image/webp", ".png": "image/png", ".woff2": "font/woff2", ".xml": "application/xml", ".txt": "text/plain; charset=utf-8",
         ".exe": "application/octet-stream"}


def _h(key, msg): return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def authorization(method, host, path, headers, payload_hash, amzdate, region, access, secret):
    names = sorted(headers)
    canonical = "\n".join([method, path, "", "".join(f"{n}:{headers[n].strip()}\n" for n in names), ";".join(names), payload_hash])
    date = amzdate[:8]
    scope = f"{date}/{region}/s3/aws4_request"
    sts = "\n".join(["AWS4-HMAC-SHA256", amzdate, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key = _h(_h(_h(_h(("AWS4" + secret).encode(), date), region), "s3"), "aws4_request")
    sig = hmac.new(key, sts.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders={';'.join(names)}, Signature={sig}"


def env(name):
    v = os.environ.get(name)
    if v: return v
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                return winreg.QueryValueEx(k, name)[0]
        except OSError:
            return None
    return None


def meta_for(rel):
    ext = os.path.splitext(rel)[1].lower()
    ctype = "application/json" if rel == "api/latest" else TYPES.get(ext) or mimetypes.guess_type(rel)[0] or "application/octet-stream"
    if ext == ".html" or rel == "api/latest": cache = "public, max-age=300"
    elif ext == ".woff2": cache = "public, max-age=31536000, immutable"
    elif ext in (".webp", ".png", ".exe"): cache = "public, max-age=3600"
    else: cache = "public, max-age=3600"
    disp = 'attachment; filename="ShabpaSetup.exe"' if ext == ".exe" else None
    return ctype, cache, disp


def put(bucket, endpoint, region, access, secret, key, data, ctype, cache, disp):
    assert key.startswith(PREFIX), "refusing to write outside " + PREFIX
    host = f"{bucket}.{endpoint}"
    path = "/" + urllib.parse.quote(key, safe="/-_.~")
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = hashlib.sha256(data).hexdigest()
    hdr = {"host": host, "x-amz-acl": "public-read", "x-amz-content-sha256": payload, "x-amz-date": now,
           "content-type": ctype, "cache-control": cache}
    if disp: hdr["content-disposition"] = disp
    auth = authorization("PUT", host, path, hdr, payload, now, region, access, secret)
    send = {k: v for k, v in hdr.items() if k != "host"}
    send.update({"Authorization": auth, "Content-Length": str(len(data))})
    req = urllib.request.Request(f"https://{host}{path}", data=data, method="PUT", headers=send)
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.status


def main(argv):
    src = os.path.abspath(argv[0] if argv else os.path.join(os.path.dirname(__file__), "..", "dist-iran-subpath"))
    if not os.path.isfile(os.path.join(src, "index.html")): sys.exit(f"{src} has no index.html. Run: node tools/build-iran-mirror.mjs --subpath")
    access, secret = env("ARVAN_ACCESS_KEY"), env("ARVAN_SECRET_KEY")
    if not access or not secret: sys.exit("ARVAN_ACCESS_KEY / ARVAN_SECRET_KEY are not set")
    bucket = os.environ.get("ARVAN_BUCKET", "shabpa-dl")
    endpoint = os.environ.get("ARVAN_ENDPOINT", "s3.ir-central1.arvanstorage.ir")
    region = os.environ.get("ARVAN_REGION", "ir-central1")

    files = []
    for dp, _, fn in os.walk(src):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), src).replace("\\", "/")
            if rel == "HOST-HEADERS.txt": continue
            files.append(rel)
    # order: installer, other assets, api, html pages last (a page never points at a missing file)
    def rank(r): return 0 if r.endswith(".exe") else 3 if r.endswith(".html") else 2 if r == "api/latest" else 1
    files.sort(key=lambda r: (rank(r), r))

    for rel in files:
        data = open(os.path.join(src, rel), "rb").read()
        ctype, cache, disp = meta_for(rel)
        key = PREFIX + rel
        try:
            status = put(bucket, endpoint, region, access, secret, key, data, ctype, cache, disp)
        except urllib.error.HTTPError as e:
            sys.exit(f"upload of {key} failed: HTTP {e.code} {e.read()[:300]!r}")
        resp = urllib.request.urlopen(f"https://{bucket}.{endpoint}/{urllib.parse.quote(key)}", timeout=600)
        back, got = resp.read(), resp.headers.get("Content-Type", "")
        if hashlib.sha256(back).digest() != hashlib.sha256(data).digest(): sys.exit(f"{key}: uploaded ({status}) but the public copy differs")
        if got.split(";")[0].strip() != ctype.split(";")[0].strip(): print(f"WARNING {key}: stored as {got!r}, wanted {ctype!r}")
        print(f"ok {key}  {len(data)} bytes  {got}")
    print(f"\nDone: {len(files)} files. Open:  https://{bucket}.{endpoint}/{PREFIX}index.html")


if __name__ == "__main__":
    main(sys.argv[1:])
