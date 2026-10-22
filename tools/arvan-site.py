#!/usr/bin/env python3
"""ArvanCloud Object Storage helper for the Shabpa mirror (S3 API, AWS Signature V4, standard library only).

  python tools/arvan-site.py upload [dir] [--prefix PREFIX]   upload a mirror bundle (default dist-iran-subpath, prefix "" = bucket root)
  python tools/arvan-site.py website get                      show the bucket's static-website settings
  python tools/arvan-site.py website set [--index index.html] [--error 404.html]
  python tools/arvan-site.py ls [prefix]                      list keys
  python tools/arvan-site.py delete <prefix> --yes            delete every key under <prefix> (never update/)

Safety rules, enforced in code:
  * keys under  update/  (the signed updater files) are never written or deleted by this tool
  * uploads are public-read with the right Content-Type / Cache-Control, installer first and the HTML pages last
  * every uploaded file is read back over public HTTPS and compared
Keys come from ARVAN_ACCESS_KEY / ARVAN_SECRET_KEY (process env, or the Windows user environment); they are never printed.
Settings: ARVAN_BUCKET (shabpa-dl)  ARVAN_ENDPOINT (s3.ir-central1.arvanstorage.ir)  ARVAN_REGION (ir-central1)
"""
import datetime, hashlib, hmac, mimetypes, os, re, sys, urllib.error, urllib.parse, urllib.request

RESERVED = "update/"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".webp": "image/webp", ".png": "image/png", ".woff2": "font/woff2", ".xml": "application/xml", ".txt": "text/plain; charset=utf-8",
         ".exe": "application/octet-stream"}


def _h(key, msg): return hmac.new(key, msg.encode(), hashlib.sha256).digest()


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


class Arvan:
    def __init__(self):
        self.access, self.secret = env("ARVAN_ACCESS_KEY"), env("ARVAN_SECRET_KEY")
        if not self.access or not self.secret: sys.exit("ARVAN_ACCESS_KEY / ARVAN_SECRET_KEY are not set")
        self.bucket = os.environ.get("ARVAN_BUCKET", "shabpa-dl")
        self.endpoint = os.environ.get("ARVAN_ENDPOINT", "s3.ir-central1.arvanstorage.ir")
        self.region = os.environ.get("ARVAN_REGION", "ir-central1")
        self.host = f"{self.bucket}.{self.endpoint}"

    def request(self, method, key="", query=None, body=b"", headers=None):
        """query: dict of query parameters. Returns (status, response headers, body). HTTP errors are returned, not raised."""
        path = "/" + urllib.parse.quote(key, safe="/-_.~")
        qs = "&".join(f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}" for k, v in sorted((query or {}).items()))
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = hashlib.sha256(body).hexdigest()
        hdr = {"host": self.host, "x-amz-content-sha256": payload, "x-amz-date": now}
        hdr.update({k.lower(): v for k, v in (headers or {}).items()})
        names = sorted(hdr)
        canonical = "\n".join([method, path, qs, "".join(f"{n}:{hdr[n].strip()}\n" for n in names), ";".join(names), payload])
        date = now[:8]
        scope = f"{date}/{self.region}/s3/aws4_request"
        sts = "\n".join(["AWS4-HMAC-SHA256", now, scope, hashlib.sha256(canonical.encode()).hexdigest()])
        k = _h(_h(_h(_h(("AWS4" + self.secret).encode(), date), self.region), "s3"), "aws4_request")
        sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
        send = {n: v for n, v in hdr.items() if n != "host"}
        send["Authorization"] = f"AWS4-HMAC-SHA256 Credential={self.access}/{scope}, SignedHeaders={';'.join(names)}, Signature={sig}"
        if body: send["Content-Length"] = str(len(body))
        req = urllib.request.Request(f"https://{self.host}{path}" + (f"?{qs}" if qs else ""), data=body or None, method=method, headers=send)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def list(self, prefix=""):
        keys, token = [], None
        while True:
            q = {"list-type": "2", "prefix": prefix}
            if token: q["continuation-token"] = token
            st, _, body = self.request("GET", "", q)
            if st != 200: sys.exit(f"list failed: HTTP {st} {body[:300]!r}")
            text = body.decode()
            keys += re.findall(r"<Key>(.*?)</Key>", text)
            m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", text)
            if not m: return keys
            token = m.group(1)


def meta_for(rel):
    ext = os.path.splitext(rel)[1].lower()
    ctype = "application/json" if rel == "api/latest" else TYPES.get(ext) or mimetypes.guess_type(rel)[0] or "application/octet-stream"
    cache = "public, max-age=31536000, immutable" if ext == ".woff2" else "public, max-age=300" if (ext == ".html" or rel == "api/latest") else "public, max-age=3600"
    disp = 'attachment; filename="ShabpaSetup.exe"' if ext == ".exe" else None
    return ctype, cache, disp


def guard(key):
    if key.startswith(RESERVED) or key == RESERVED.rstrip("/"): sys.exit(f"refusing to touch {key!r}: update/ holds the signed updater files")


def cmd_upload(a, argv):
    prefix, pos = "", []
    i = 0
    while i < len(argv):
        if argv[i] == "--prefix": prefix = argv[i + 1]; i += 2
        else: pos.append(argv[i]); i += 1
    src = os.path.abspath(pos[0] if pos else os.path.join(os.path.dirname(__file__), "..", "dist-iran-subpath"))
    if not os.path.isfile(os.path.join(src, "index.html")): sys.exit(f"{src} has no index.html. Run: node tools/build-iran-mirror.mjs --subpath")
    files = []
    for dp, _, fn in os.walk(src):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), src).replace("\\", "/")
            if rel != "HOST-HEADERS.txt": files.append(rel)
    files.sort(key=lambda r: (0 if r.endswith(".exe") else 3 if r.endswith(".html") else 2 if r == "api/latest" else 1, r))
    for rel in files:
        key = prefix + rel
        guard(key)
        data = open(os.path.join(src, rel), "rb").read()
        ctype, cache, disp = meta_for(rel)
        h = {"x-amz-acl": "public-read", "content-type": ctype, "cache-control": cache}
        if disp: h["content-disposition"] = disp
        st, _, body = a.request("PUT", key, None, data, h)
        if st not in (200, 201): sys.exit(f"upload of {key} failed: HTTP {st} {body[:300]!r}")
        resp = urllib.request.urlopen(f"https://{a.host}/{urllib.parse.quote(key)}", timeout=600)
        back, got = resp.read(), resp.headers.get("Content-Type", "")
        if hashlib.sha256(back).digest() != hashlib.sha256(data).digest(): sys.exit(f"{key}: uploaded ({st}) but the public copy differs")
        flag = "" if got.split(";")[0].strip() == ctype.split(";")[0].strip() else f"   WARNING stored as {got!r}"
        print(f"ok {key}  {len(data)} bytes{flag}")
    print(f"\nDone: {len(files)} files under '{prefix}'. Open: https://{a.host}/{prefix}index.html")


def cmd_website(a, argv):
    if argv[:1] == ["get"]:
        st, _, body = a.request("GET", "", {"website": ""})
        print(st, body.decode(errors="replace")[:600]); return
    if argv[:1] == ["set"]:
        index, error = "index.html", "404.html"
        for i, t in enumerate(argv):
            if t == "--index": index = argv[i + 1]
            if t == "--error": error = argv[i + 1]
        xml = ('<?xml version="1.0" encoding="UTF-8"?><WebsiteConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
               f"<IndexDocument><Suffix>{index}</Suffix></IndexDocument><ErrorDocument><Key>{error}</Key></ErrorDocument></WebsiteConfiguration>").encode()
        st, _, body = a.request("PUT", "", {"website": ""}, xml, {"content-type": "application/xml"})
        print(st, body.decode(errors="replace")[:600]); return
    sys.exit(__doc__)


def cmd_delete(a, argv):
    if len(argv) < 2 or argv[1] != "--yes": sys.exit("usage: delete <prefix> --yes")
    prefix = argv[0]
    if not prefix or prefix.startswith(RESERVED): sys.exit("refusing: empty prefix or update/")
    keys = a.list(prefix)
    for k in keys:
        guard(k)
        st, _, body = a.request("DELETE", k)
        print("deleted" if st in (200, 204) else f"FAILED {st}", k)
    print(f"{len(keys)} key(s) under {prefix!r}")


def main(argv):
    if not argv: sys.exit(__doc__)
    a = Arvan()
    cmd, rest = argv[0], argv[1:]
    if cmd == "upload": cmd_upload(a, rest)
    elif cmd == "website": cmd_website(a, rest)
    elif cmd == "ls": print("\n".join(a.list(rest[0] if rest else "")))
    elif cmd == "delete": cmd_delete(a, rest)
    else: sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
