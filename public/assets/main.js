"use strict";
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  var LANG = document.documentElement.lang === "en" ? "en" : "fa";
  /* ریشه‌ی سایت: روی shabpa.ir همون "/" ؛ روی آینه‌ای که توی یه زیرپوشه میزبانی می‌شه، صفحه با meta می‌گه ریشه کجاست */
  function meta(n) { var m = document.querySelector('meta[name="' + n + '"]'); return m ? m.getAttribute("content") : null; }
  var ROOT = new URL(meta("site-root") || "/", location.href).href;
  var INDEX = meta("site-index") || "";
  var T = {
    fa: {
      mb: " مگابایت", copy: "کپی", copied: "کپی شد", locale: "fa-IR",
      say: function (act, n) { return "سیستم " + act + " می‌شه؛ قبلش " + n + " ثانیه فرصت لغو داری."; },
      canceled: "لغو شد. هیچ اتفاقی نیفتاد، همین‌قدر ساده.", done: "تموم شد.", woke: "بیدار شدی! دوباره امتحانش کن."
    },
    en: {
      mb: " MB", copy: "Copy", copied: "Copied", locale: "en-US",
      say: function (act, n) { return act + " in " + n + " s. You can still cancel."; },
      canceled: "Canceled. Nothing happened, just that simple.", done: "Done.", woke: "You're back! Try it again."
    }
  }[LANG];
  var FA = "۰۱۲۳۴۵۶۷۸۹";
  var fa = function (v) { return LANG === "en" ? String(v) : String(v).replace(/\d/g, function (d) { return FA[d]; }); };
  var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); };
  var smooth = function (t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
  var lerp = function (a, b, t) { return a + (b - a) * t; };

  /* ---------- رنگ آسمان بر اساس پیشرفت اسکرول ---------- */
  function hex(h) { return [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  var KEYS = [
    { p: 0.00, c: ["#3f9cff", "#7cc6ff", "#d8f0ff"], hf: "#8fb6e0", hn: "#6f9bc9", b: "#5d88b8", t: "#4f79a8", sun: "#fff3b0" },
    { p: 0.28, c: ["#4a8fe0", "#9cc2ee", "#ffe3b8"], hf: "#8aa9cf", hn: "#7194bd", b: "#5f7fa9", t: "#52709a", sun: "#ffe08a" },
    { p: 0.44, c: ["#3a3f95", "#c2607a", "#ffa25e"], hf: "#5a4a86", hn: "#3f3468", b: "#33295a", t: "#2d2452", sun: "#ff9a4a" },
    { p: 0.58, c: ["#1a1b52", "#4a2f7a", "#c0587a"], hf: "#2a2459", hn: "#1c1a45", b: "#161437", t: "#141233", sun: "#ff7a45" },
    { p: 0.74, c: ["#0c0f33", "#1a1a5a", "#3a2f7a"], hf: "#171845", hn: "#0f1030", b: "#0b0c26", t: "#0a0b22", sun: "#ff7a45" },
    { p: 1.00, c: ["#04061a", "#0a0d33", "#171250"], hf: "#0d0f33", hn: "#080a22", b: "#05061a", t: "#05061a", sun: "#ff7a45" }
  ].map(function (k) {
    return { p: k.p, c: k.c.map(hex), hf: hex(k.hf), hn: hex(k.hn), b: hex(k.b), t: hex(k.t), sun: hex(k.sun) };
  });
  function mix(a, b, t) { return "rgb(" + a.map(function (v, i) { return Math.round(lerp(v, b[i], t)); }).join(",") + ")"; }
  function sample(p) {
    var i = 0;
    while (i < KEYS.length - 2 && p > KEYS[i + 1].p) i++;
    var a = KEYS[i], b = KEYS[i + 1], t = clamp((p - a.p) / (b.p - a.p), 0, 1);
    return {
      c: a.c.map(function (col, n) { return mix(col, b.c[n], t); }),
      hf: mix(a.hf, b.hf, t), hn: mix(a.hn, b.hn, t), b: mix(a.b, b.b, t), t: mix(a.t, b.t, t), sun: mix(a.sun, b.sun, t)
    };
  }

  var body = document.body;
  var clockTime = $("#clockTime");
  var progress = 0, lastNight = null, lastClock = "", lastP = -1, starsO = 0, cloudsGone = null;
  var sky = $(".sky"), themeMeta = $('meta[name="theme-color"]');
  /* دستگاه ضعیف یا حالت صرفه‌جویی داده: افکت‌های سنگین خاموش می‌شن */
  var conn = navigator.connection || {};
  var forced = /[?&]lite=([01])/.exec(location.search);
  var lite = forced ? forced[1] === "1" : (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 4 || conn.saveData === true || /(^|-)2g$|3g/.test(conn.effectiveType || "");
  if (lite) root.classList.add("lite");
  /* متغیرهای آسمان فقط روی خود آسمان نوشته می‌شن تا استایل کل صفحه دوباره محاسبه نشه */
  var skyGrad = $(".sky-grad"), hor = $(".horizon"), sunEl = $(".sun"), moonEl = $(".moon"), cloudsEl = $(".clouds"), starsEl = $("#stars");
  var lightsEl = null; /* گروه پنجره‌های شهر؛ بعد از ساختنشون پر می‌شه */
  var target = 1;
  function measure() {
    var dl = $("#download");
    /* شب کامل وقتی بخش دانلود تقریباً وسط صفحه‌ست */
    target = dl ? Math.max(1, dl.getBoundingClientRect().top + window.scrollY - window.innerHeight * 0.3) : Math.max(1, root.scrollHeight - window.innerHeight);
    lastP = -1;
  }

  function update() {
    progress = clamp(window.scrollY / target, 0, 1);
    var p = progress;
    if (Math.abs(p - lastP) < 0.0004) return;
    lastP = p;
    var s = sample(p), vw = window.innerWidth, vh = window.innerHeight;

    skyGrad.style.background = "linear-gradient(180deg," + s.c[0] + " 0%," + s.c[1] + " 55%," + s.c[2] + " 100%)";
    var hs = hor.style;
    hs.setProperty("--hill-far", s.hf); hs.setProperty("--hill-near", s.hn); hs.setProperty("--bld", s.b); hs.setProperty("--tower", s.t);

    /* خورشید: از بالا به افق می‌ره و غروب می‌کنه */
    var sp = clamp(p / 0.52, 0, 1);
    var sunSize = Math.min(Math.max(vw * 0.12, 90), 170);
    var sx = Math.round(lerp(vw < 900 ? vw * 0.12 : vw * 0.47, vw * 0.5, sp) - sunSize / 2), sy = Math.round(lerp(vh * 0.1, vh * 0.98, smooth(sp)));
    var so2 = 1 - smooth((p - 0.46) / 0.1);
    sunEl.style.transform = "translate(" + sx + "px," + sy + "px)"; sunEl.style.opacity = String(so2);
    sunEl.style.visibility = so2 < 0.01 ? "hidden" : "visible"; sunEl.style.setProperty("--sun-c", s.sun);
    /* ماه: از پایین بالا میاد */
    var mp = clamp((p - 0.5) / 0.32, 0, 1);
    var mo = smooth((p - 0.5) / 0.1);
    moonEl.style.transform = "translate(" + Math.round(lerp(vw * 0.12, vw * 0.2, mp)) + "px," + Math.round(lerp(vh * 1.05, vh * (vw < 900 ? 0.2 : 0.16), smooth(mp))) + "px)";
    moonEl.style.opacity = String(mo); moonEl.style.visibility = mo < 0.01 ? "hidden" : "visible";
    starsO = smooth((p - 0.5) / 0.25);
    starsEl.style.opacity = String(starsO);
    var co = 1 - smooth(p / 0.5);
    cloudsEl.style.opacity = String(co);
    var gone = co < 0.02;
    if (gone !== cloudsGone) { sky.classList.toggle("no-clouds", gone); cloudsGone = gone; }
    var wa = smooth((p - 0.55) / 0.2);
    if (lightsEl) lightsEl.style.opacity = String((wa * 0.9).toFixed(3));
    hs.setProperty("--win-a", String(wa.toFixed(3)));
    ensureLoop();

    var night = p > 0.4;
    if (night !== lastNight) { body.classList.toggle("night", night); lastNight = night; }
    if (themeMeta) themeMeta.setAttribute("content", s.c[0]);

    /* ساعت: ۱۲:۰۰ ظهر تا ۰۳:۰۰ بامداد */
    var mins = Math.round(lerp(12 * 60, 27 * 60, p) / 5) * 5, h = Math.floor(mins / 60) % 24, m = mins % 60;
    var txt = fa((h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m);
    if (txt !== lastClock) { clockTime.textContent = txt; lastClock = txt; }
  }

  var ticking = false;
  function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(function () { ticking = false; update(); }); } }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", function () { sizeStars(); measure(); update(); });
  window.addEventListener("load", function () { measure(); update(); });
  if ("ResizeObserver" in window) { var ro = new ResizeObserver(function () { measure(); onScroll(); }); ro.observe(document.body); }

  /* ---------- ستاره‌ها ---------- */
  var cv = $("#stars"), ctx = cv.getContext("2d"), stars = [], shoot = null, W = 0, H = 0, lastShoot = 0;
  function sizeStars() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var n = lite ? 60 : Math.round(clamp(W * H / 7000, 70, 220));
    stars = [];
    for (var i = 0; i < n; i++) stars.push({ x: Math.random() * W, y: Math.random() * H * 0.78, r: Math.random() * 1.3 + 0.3, ph: Math.random() * 6.28, sp: 0.5 + Math.random() * 1.5 });
  }
  function drawStars(t) {
    ctx.clearRect(0, 0, W, H);
    var so = starsO;
    if (so < 0.02) return;
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i], a = reduce ? 0.8 : 0.45 + 0.55 * Math.abs(Math.sin(t / 1000 * s.sp + s.ph));
      ctx.globalAlpha = a; ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.283); ctx.fill();
    }
    if (!reduce && !lite) {
      if (!shoot && so > 0.8 && t - lastShoot > 5500 && Math.random() < 0.01) {
        shoot = { x: Math.random() * W * 0.7 + W * 0.2, y: Math.random() * H * 0.3, vx: -6 - Math.random() * 3, vy: 3 + Math.random() * 2, life: 1 };
        lastShoot = t;
      }
      if (shoot) {
        var g = ctx.createLinearGradient(shoot.x, shoot.y, shoot.x - shoot.vx * 9, shoot.y - shoot.vy * 9);
        g.addColorStop(0, "rgba(255,255,255," + shoot.life + ")"); g.addColorStop(1, "rgba(255,255,255,0)");
        ctx.globalAlpha = 1; ctx.strokeStyle = g; ctx.lineWidth = 2; ctx.beginPath();
        ctx.moveTo(shoot.x, shoot.y); ctx.lineTo(shoot.x - shoot.vx * 9, shoot.y - shoot.vy * 9); ctx.stroke();
        shoot.x += shoot.vx; shoot.y += shoot.vy; shoot.life -= 0.018;
        if (shoot.life <= 0) shoot = null;
      }
    }
    ctx.globalAlpha = 1;
  }
  var raf = 0, lastDraw = 0, FRAME = lite ? 66 : 33;
  function loop(t) {
    raf = 0;
    if (document.hidden || starsO < 0.02) { ctx.clearRect(0, 0, W, H); return; }
    if (t - lastDraw >= FRAME) { lastDraw = t; drawStars(t); }
    raf = requestAnimationFrame(loop);
  }
  function ensureLoop() { if (!raf && !document.hidden && starsO >= 0.02) raf = requestAnimationFrame(loop); }
  document.addEventListener("visibilitychange", function () { if (!document.hidden) ensureLoop(); });

  /* ---------- پنجره‌های شهر ---------- */
  (function windows() {
    var g = $("#city"), ns = "http://www.w3.org/2000/svg", seed = 7;
    var lg = document.createElementNS(ns, "g"); lg.setAttribute("class", "lights"); g.appendChild(lg); lightsEl = lg;
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    var cols = [[40, 34, 62], [130, 30, 88], [214, 46, 56], [300, 26, 104], [390, 38, 70], [470, 34, 92], [560, 48, 58], [650, 28, 110],
      [1200, 30, 96], [1290, 46, 62], [1380, 26, 108], [1460, 38, 74], [1530, 50, 60]];
    cols.forEach(function (b) {
      for (var y = 320 - b[2] + 10; y < 312; y += 14) {
        for (var x = b[0] + 5; x < b[0] + b[1] - 6; x += 10) {
          if (rnd() < 0.45) {
            var r = document.createElementNS(ns, "rect");
            r.setAttribute("x", x); r.setAttribute("y", y); r.setAttribute("width", 4); r.setAttribute("height", 6);
            r.setAttribute("class", "win-l"); lg.appendChild(r);
          }
        }
      }
    });
  })();

  /* ---------- ریل امکانات ---------- */
  var rail = $("#rail"), railLinks = [];
  $$("[data-title]").forEach(function (sec, i) {
    sec.id = sec.id || "sec" + (i + 1);
    var a = document.createElement("a");
    a.href = "#" + sec.id; a.setAttribute("aria-label", sec.getAttribute("data-title"));
    var sp = document.createElement("span"); sp.textContent = sec.getAttribute("data-title"); a.appendChild(sp);
    rail.appendChild(a); railLinks.push({ a: a, el: sec });
  });

  /* ---------- ظاهر شدن بخش‌ها ---------- */
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.18, rootMargin: "0px 0px -6% 0px" });
  $$(".reveal, .chap, .themes, .trust, .download .dl-card, .shutdown").forEach(function (el) { io.observe(el); });

  var active = new IntersectionObserver(function () {
    var mid = window.innerHeight * 0.45, best = null, bd = 1e9;
    railLinks.forEach(function (r) {
      var b = r.el.getBoundingClientRect(), d = Math.abs((b.top + b.bottom) / 2 - mid);
      if (b.top < mid && b.bottom > mid) d = 0;
      if (d < bd) { bd = d; best = r; }
    });
    railLinks.forEach(function (r) { r.a.classList.toggle("on", r === best); });
  }, { threshold: [0, 0.25, 0.5, 0.75, 1] });
  railLinks.forEach(function (r) { active.observe(r.el); });

  /* ---------- کج‌شدن اسکرین‌شات با ماوس ---------- */
  if (!reduce && !lite && window.matchMedia("(hover:hover)").matches) {
    $$("[data-tilt]").forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        var b = el.getBoundingClientRect(), x = (e.clientX - b.left) / b.width - 0.5, y = (e.clientY - b.top) / b.height - 0.5;
        el.style.transform = "perspective(1000px) rotateY(" + (x * 7).toFixed(2) + "deg) rotateX(" + (-y * 6).toFixed(2) + "deg)";
      });
      el.addEventListener("pointerleave", function () { el.style.transform = ""; });
    });
  }

  /* ---------- نمایش بزرگ تصویر ---------- */
  var lb = $("#lightbox"), lbImg = $("#lbImg");
  $$(".win img").forEach(function (img) {
    img.addEventListener("click", function () {
      if (typeof lb.showModal !== "function") return;
      lbImg.src = img.currentSrc || img.src; lbImg.alt = img.alt; lb.showModal();
    });
  });
  $("#lbClose").addEventListener("click", function () { lb.close(); });
  lb.addEventListener("click", function (e) { if (e.target === lb) lb.close(); });

  /* ---------- آخرین نسخه (از خود سایت؛ سرور اطلاعات و فایل رو از GitHub می‌گیره و کش می‌کنه) ---------- */
  var OK_URL = /^https:\/\/github\.com\/MrPitPot\/shabpa\/releases\/download\/v\d+\.\d+\.\d+\/ShabpaSetup\.exe$/;
  function applyRelease(d) {
    if (!d || typeof d.version !== "string" || !/^\d+\.\d+\.\d+$/.test(d.version) || (d.url !== "/download/ShabpaSetup.exe" && d.url !== "download/ShabpaSetup.exe")) return;
    var dlHref = new URL(d.url, ROOT).href;
    ["#heroDl", "#dlBtn"].forEach(function (s) { $(s).href = dlHref; });
    $("#heroVer").textContent = "v" + d.version; $("#dlVer").textContent = "v" + d.version;
    $("#dlFile").textContent = d.file;
    $("#dlSize").textContent = fa((d.size / 1048576).toFixed(1)) + T.mb;
    var dt = new Date(d.published);
    if (!isNaN(dt)) $("#dlDate").textContent = new Intl.DateTimeFormat(T.locale, { dateStyle: "long" }).format(dt);
    $("#dlMeta").hidden = false;
    if (/^[0-9a-f]{64}$/.test(d.sha256)) { $("#shaVal").textContent = d.sha256; $("#shaBox").hidden = false; }
    var alt = $("#dlAlt");
    if (alt && typeof d.github === "string" && OK_URL.test(d.github)) alt.href = d.github;
  }
  (function fetchRelease() {
    var cached = null;
    try { cached = JSON.parse(sessionStorage.getItem("shabpa-rel3") || "null"); } catch (e) { /* ignore */ }
    if (cached && Date.now() - cached.t < 600000) { applyRelease(cached.d); return; }
    var ctl = "AbortController" in window ? new AbortController() : null;
    var to = setTimeout(function () { if (ctl) ctl.abort(); }, 10000);
    fetch(ROOT + "api/latest", { signal: ctl ? ctl.signal : undefined, credentials: "omit" })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) {
        clearTimeout(to); applyRelease(d);
        try { sessionStorage.setItem("shabpa-rel3", JSON.stringify({ t: Date.now(), d: d })); } catch (e) { /* ignore */ }
      })
      .catch(function () { /* لینک ثابت «آخرین نسخه» توی GitHub می‌مونه */ });
  })();

  $("#shaCopy").addEventListener("click", function () {
    var btn = this, v = $("#shaVal").textContent;
    var done = function () { btn.textContent = T.copied; setTimeout(function () { btn.textContent = T.copy; }, 1800); };
    if (navigator.clipboard) navigator.clipboard.writeText(v).then(done, function () {});
  });

  /* ---------- شمارنده‌ی آمار ---------- */
  var cio = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      cio.unobserve(e.target);
      var el = $("b", e.target), to = parseInt(el.getAttribute("data-count"), 10);
      if (isNaN(to) || reduce || to === 0) return;
      var t0 = performance.now();
      (function step(t) {
        var k = clamp((t - t0) / 1100, 0, 1);
        el.textContent = fa(Math.round(to * smooth(k)));
        if (k < 1) requestAnimationFrame(step);
      })(t0);
    });
  }, { threshold: 0.6 });
  $$(".stat").forEach(function (el) { cio.observe(el); });

  /* ---------- شبیه‌ساز خاموشی (فقط نمایشه، به سیستم دست نمی‌زنه) ---------- */
  (function sim() {
    var seg = $("#seg"), ring = $("#ring"), fg = $("#ringFg"), num = $("#simNum"), msg = $("#simMsg");
    var go = $("#simGo"), cancel = $("#simCancel"), off = $("#off"), wake = $("#offWake");
    var TOTAL = 10, CIRC = 326.7, act = $(".on", seg).getAttribute("data-act"), left = TOTAL, timer = 0;
    function paint() {
      num.textContent = fa(left);
      fg.style.strokeDashoffset = String((CIRC * (TOTAL - left) / TOTAL).toFixed(1));
      ring.classList.toggle("warn", timer !== 0 && left <= 3);
    }
    function reset(text) {
      clearInterval(timer); timer = 0; left = TOTAL;
      ring.classList.remove("run", "warn"); seg.classList.remove("locked");
      go.disabled = false; cancel.disabled = true; msg.textContent = text; paint();
    }
    seg.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b || timer) return;
      $$("button", seg).forEach(function (x) { var on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-checked", on ? "true" : "false"); });
      act = b.getAttribute("data-act");
    });
    function say() { msg.textContent = T.say(act, fa(left)); }
    go.addEventListener("click", function () {
      if (timer) return;
      left = TOTAL; ring.classList.add("run"); seg.classList.add("locked"); go.disabled = true; cancel.disabled = false; say(); paint();
      timer = setInterval(function () {
        left--; paint();
        if (left <= 0) { clearInterval(timer); timer = 0; finish(); } else say();
      }, 1000);
    });
    cancel.addEventListener("click", function () { reset(T.canceled); });
    function finish() {
      msg.textContent = T.done;
      off.hidden = false; wake.focus();
    }
    function wakeUp() {
      off.hidden = true; reset(T.woke);
      go.focus({ preventScroll: true });
    }
    wake.addEventListener("click", wakeUp);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !off.hidden) wakeUp(); });
    paint();
  })();

  /* ---------- زبان: دکمه‌ی بالا + پیشنهاد یک‌باره ---------- */
  (function lang() {
    var KEY = "shabpa-lang", sw = $("#langSwitch");
    function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
    function set(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* ignore */ } }
    if (sw) sw.addEventListener("click", function (e) {
      set(sw.getAttribute("data-lang"));
      if (location.hash) { e.preventDefault(); location.href = sw.getAttribute("href") + location.hash; }
    });
    var pref = get();
    if (pref === "fa" || pref === "en") {
      /* کاربری که قبلاً انگلیسی رو انتخاب کرده، روی صفحه‌ی اصلی به نسخه‌ی خودش می‌رسه (لینک مستقیم /en/ هیچ‌وقت منحرف نمی‌شه) */
      var rootPath = new URL(ROOT).pathname, onRoot = location.pathname === rootPath || location.pathname === rootPath + INDEX;
      if (pref === "en" && LANG === "fa" && onRoot && !location.hash) location.replace(ROOT + "en/" + INDEX);
      return;
    }
    var langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
    var wantsFa = /^fa/i.test(langs[0] || "");
    if ((LANG === "fa") === wantsFa) return;
    var other = LANG === "fa" ? "en" : "fa";
    var bar = document.createElement("div"); bar.className = "lang-bar"; bar.setAttribute("role", "region");
    var a = document.createElement("a"); a.className = "btn btn-sm";
    a.href = other === "en" ? ROOT + "en/" + INDEX : ROOT + INDEX; a.setAttribute("hreflang", other);
    var x = document.createElement("button"); x.type = "button"; x.className = "lang-x";
    if (other === "en") { bar.setAttribute("aria-label", "Language"); bar.lang = "en"; bar.dir = "ltr"; a.textContent = "View in English"; x.textContent = "No thanks"; }
    else { bar.setAttribute("aria-label", "زبان"); bar.lang = "fa"; bar.dir = "rtl"; a.textContent = "مشاهده‌ی سایت به فارسی"; x.textContent = "نه، ممنون"; }
    a.addEventListener("click", function () { set(other); });
    x.addEventListener("click", function () { set(LANG); bar.remove(); });
    bar.appendChild(a); bar.appendChild(x); document.body.appendChild(bar);
  })();

  sizeStars(); measure(); update();
})();
