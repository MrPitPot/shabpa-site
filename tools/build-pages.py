#!/usr/bin/env python3
"""Generates the static guide pages (one landing page per feature, Persian and English).

    python tools/build-pages.py

Writes public/<slug>/index.html and public/en/<slug>/index.html, the guide list that the two home pages show
(between the <!--guides--> markers) and public/sitemap.xml. Plain static output, no runtime dependencies.
Every page uses only the existing stylesheet: no inline script, no inline style, so the strict CSP in _headers still holds.
"""
import html
import json
import os
import re
import sys

APP = os.environ.get("SHABPA_APP_DIR") or next((d for d in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", n) for n in ("Shabpa-boofi", "Shabpa")) if os.path.exists(os.path.join(d, "CHANGELOG.md"))), "")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
SITE = "https://shabpa.ir"
LASTMOD = "2026-10-31"
CSS_V = "20261031"
e = html.escape

PAGES = [
    {
        "slug": "shutdown-timer", "img": "power", "alt": {"fa": "کنترل سیستم: خاموش، خواب، هایبرنیت و ریستارت با شمارش معکوس", "en": "System control: shut down, sleep, hibernate and restart with a countdown"},
        "fa": {
            "name": "تایمر خاموشی",
            "title": "تایمر خاموش شدن خودکار کامپیوتر در ویندوز ۱۰ و ۱۱ | شب‌پا",
            "desc": "با شب‌پا کامپیوتر رو سر ساعت یا بعد از تموم شدن دانلود خودکار خاموش کن. خواب، هایبرنیت و ریستارت زمان‌بندی‌شده با شمارش معکوس قابل لغو؛ رایگان و فارسی.",
            "h1": "خاموش کردن خودکار کامپیوتر، سر وقت و بدون دردسر",
            "lead": "اگه شب‌ها فیلم، دانلود یا بازی رو نیمه‌کاره ول می‌کنی و کامپیوتر تا صبح روشن می‌مونه، یه تایمر خاموشی خوب لازم داری. شب‌پا خاموشی، خواب، هایبرنیت و ریستارت رو زمان‌بندی می‌کنه و قبل از هر کدوم یه شمارش معکوس نشون می‌ده که هر لحظه می‌تونی لغوش کنی.",
            "steps_h": "چطور کامپیوتر رو خودکار خاموش کنم؟",
            "steps": ["شب‌پا رو باز کن و از منوی کنار، «کنترل سیستم» و بعد تب «دستور برق» رو بزن.", "نوع دستور رو انتخاب کن: خاموش، خواب، هایبرنیت یا ریستارت.", "زمان رو بذار: همین الان، چند دقیقه یا چند ساعت دیگه، یا یه ساعت مشخص. برای تکرار هر شب، برنامه‌ی تکرارشونده بساز (مثلاً هر شب ۱:۳۰).", "تأیید رو بزن. کارت تأیید زمان دقیق اجرا رو نشون می‌ده و قبل از خاموشی هم شمارش معکوس روی صفحه میاد."],
            "alt_line": "راه سریع‌تر: Ctrl+Alt+Space رو بزن و بنویس «ساعت ۱ شب خاموش کن» یا «یه ساعت و ربع دیگه بخوابون». دستیار شب‌پا کاملاً آفلاین کار می‌کنه.",
            "feat_h": "چیزهایی که یه تایمر معمولی ندارد",
            "feats": ["خاموشی شرطی: وقتی دانلود یا آپلود تموم شد، سیستم بیکار شد، یه برنامه بسته شد یا یه کار سنگین تموم شد", "تایمر بیدارباش برای بیدار کردن سیستم از خواب", "تاریخچه‌ی خواب و بیداری و مصرف برق", "دستور دیررسیده هرگز اجرا نمی‌شه: اگه کامپیوتر موقع زمان خاموشی خاموش یا خواب بوده، بعداً ناگهان خاموش نمی‌شه", "هر زمان‌بندی قبل از ثبت، زمان دقیقش رو نشون می‌ده و تأیید می‌گیره"],
            "faq": [("اگه وسط کار خاموش بشه چی؟", "قبل از خاموشی یه شمارش معکوس روی صفحه میاد و می‌تونی لغوش کنی. زمان شمارش از قبل مشخصه."), ("بعد از تموم شدن دانلود خودکار خاموش می‌شه؟", "بله. توی «خاموشی شرطی» شرط «وقتی دانلود تموم شد» رو انتخاب کن؛ سیستم وقتی مصرف اینترنت پایین بیاد، با همون شمارش معکوس خاموش می‌شه.")],
        },
        "en": {
            "name": "Shutdown timer",
            "title": "Auto Shutdown Timer for Windows 10 and 11 | Shabpa",
            "desc": "Shut your PC down on schedule or when a download finishes with Shabpa. Timed sleep, hibernate and restart with a cancellable countdown. Free and open source.",
            "h1": "Shut your PC down automatically, on time and without surprises",
            "lead": "If you fall asleep during a movie, a download or a game and the PC runs until morning, you need a good shutdown timer. Shabpa schedules shutdown, sleep, hibernate and restart, and shows a countdown before each one that you can cancel at any moment.",
            "steps_h": "How do I shut down my PC automatically?",
            "steps": ["Open Shabpa, choose \"System control\" from the side menu and then the \"Power command\" tab.", "Pick the action: shut down, sleep, hibernate or restart.", "Set the time: right now, in a few minutes or hours, or at an exact time. For every night, create a repeating schedule (say, every night at 1:30).", "Confirm. A card shows the exact time it will run, and a countdown appears on screen before the shutdown."],
            "alt_line": "A faster way: press Ctrl+Alt+Space and type \"shut down at 1 am\" or \"sleep in an hour and a quarter\". Shabpa's command box works fully offline.",
            "feat_h": "What an ordinary timer does not give you",
            "feats": ["Conditional shutdown: when a download or upload finishes, the PC goes idle, a program closes or a heavy task ends", "Wake timers to bring the PC back from sleep", "Sleep and wake history and power use", "A late command never runs: if the PC was off or asleep at the scheduled time, it will not shut down by surprise later", "Every schedule shows its exact time and asks for confirmation before it is saved"],
            "faq": [("What if it shuts down in the middle of my work?", "A countdown appears on screen first and you can cancel it. The length of the countdown is known in advance."), ("Can it shut down after a download finishes?", "Yes. In \"Conditional shutdown\" choose \"when the download finishes\"; once network use drops, the PC shuts down with the same countdown.")],
        },
    },
    {
        "slug": "game-overlay", "img": "overlay", "alt": {"fa": "تنظیمات اورلی بازی: چیدمان، رنگ و اندازه", "en": "Game overlay settings: layout, color and size"},
        "fa": {
            "name": "اورلی بازی",
            "title": "نمایش FPS، دما و پینگ روی بازی؛ اورلی بازی ویندوز | شب‌پا",
            "desc": "اورلی رایگان شب‌پا FPS، ۱٪ پایین، دمای کارت گرافیک و پردازنده، رم و پینگ رو روی بازی نشون می‌ده. شش چیدمان، رنگ و اندازه‌ی دلخواه، بدون تزریق به بازی.",
            "h1": "نمایش FPS، دما و پینگ روی بازی، با ظاهر دلخواه",
            "lead": "اورلی بازی شب‌پا اطلاعات سیستم رو روی بازی نشون می‌ده تا بدونی کارت گرافیک یا پردازنده کی داغ می‌کنه و کی فریم می‌افته. چیزی داخل بازی تزریق نمی‌شه و فقط روی صفحه کشیده می‌شه.",
            "steps_h": "چطور اورلی FPS رو روشن کنم؟",
            "steps": ["شب‌پا رو باز کن و «اورلی بازی» رو از منوی کنار بزن.", "توی بخش «نمایش» یکی از حالت‌ها رو بذار: خاموش، فقط موقع بازی یا همیشه.", "یکی از شش چیدمان رو انتخاب کن: کارت، نوار افقی، فشرده، مینیمال، حلقه‌ای یا نمودار.", "اندازه (۲۵ تا ۲۰۰٪)، تیرگی پس‌زمینه (۰ تا ۱۰۰٪) و رنگ هر بخش رو تنظیم کن؛ پیش‌نمایش همون لحظه عوض می‌شه."],
            "alt_line": "اگه شب‌پا بازی‌ات رو نمی‌شناسه، اسم برنامه‌اش رو (مثلاً cs2 یا valorant) توی همون صفحه بنویس.",
            "feat_h": "امکانات اورلی",
            "feats": ["FPS، ۱٪ پایین، بار و دمای کارت گرافیک، بار و دمای پردازنده، رم، پینگ و ساعت (حتی با ثانیه)", "رنگ جدا برای فریم‌ریت، GPU، CPU، RAM، NET و ساعت", "پروفایل جدا برای هر بازی و گزارش بعد از بازی", "اورلی رو با ماوس هر جا خواستی بکش", "هیچ چیزی داخل بازی تزریق نمی‌شه"],
            "faq": [("اورلی شب‌پا باعث بن شدن می‌شه؟", "اورلی چیزی داخل بازی تزریق نمی‌کنه و فقط روی صفحه کشیده می‌شه، برای همین با ضدتقلب‌ها مشکلی نداره. با این حال برای هیچ ضدتقلب مشخصی تضمین نمی‌دیم؛ اگه بازی‌ات خیلی سخت‌گیره، قوانینش رو هم نگاه کن."), ("چرا بعضی عددها خالی‌ان؟", "فریم بر ثانیه، دمای پردازنده و فن‌ها دسترسی ادمین می‌خوان. اگه شب‌پا رو با دسترسی ادمین اجرا کنی پر می‌شن؛ بقیه‌ی عددها بدون ادمین هم کار می‌کنن.")],
        },
        "en": {
            "name": "Game overlay",
            "title": "FPS, Temperature and Ping Overlay for Games | Shabpa",
            "desc": "Shabpa's free game overlay shows FPS, 1% low, GPU and CPU temperature, RAM and ping over your game. Six layouts, your own colors and size, nothing injected into the game.",
            "h1": "FPS, temperatures and ping over your game, your way",
            "lead": "Shabpa's game overlay puts system info over your game so you can see when the GPU or CPU gets hot and when frames drop. Nothing is injected into the game; it is only drawn on screen.",
            "steps_h": "How do I turn on an FPS overlay?",
            "steps": ["Open Shabpa and choose \"Game overlay\" from the side menu.", "Under \"Display\" pick a mode: off, only in game or always.", "Choose one of six layouts: card, horizontal bar, compact, minimal, rings or graph.", "Set the size (25 to 200%), background opacity (0 to 100%) and the color of each part; the preview updates instantly."],
            "alt_line": "If Shabpa does not recognize your game, type its program name (for example cs2 or valorant) on the same page.",
            "feat_h": "What the overlay shows",
            "feats": ["FPS, 1% low, GPU load and temperature, CPU load and temperature, RAM, ping and a clock (even with seconds)", "A separate color for frame rate, GPU, CPU, RAM, NET and the clock", "A separate profile per game and a report after each session", "Drag the overlay anywhere with the mouse", "Nothing is injected into the game"],
            "faq": [("Can the Shabpa overlay get me banned?", "The overlay injects nothing into the game and is only drawn on screen, so it does not interfere with anti-cheat. Still, we cannot guarantee it for any specific anti-cheat; if your game is very strict, check its own rules too."), ("Why are some numbers empty?", "Frame rate, CPU temperature and fans need administrator rights. Run Shabpa as administrator and they fill in; the other numbers work without it.")],
        },
    },
    {
        "slug": "lower-ping", "img": "ping", "alt": {"fa": "پایداری پینگ و محافظ موقع بازی", "en": "Ping stability and in-game protection"},
        "fa": {
            "name": "کنترل اینترنت و پینگ",
            "title": "محدود کردن سرعت اینترنت برنامه‌ها و پایدار کردن پینگ بازی | شب‌پا",
            "desc": "ببین کدوم برنامه اینترنتت رو می‌خوره و سقف سرعتش رو بذار. محافظ موقع بازی شب‌پا خودکار سرعت بقیه‌ی برنامه‌ها رو محدود می‌کنه تا پینگ نپره. رایگان.",
            "h1": "ببین کی اینترنتت رو می‌خوره و جلوش رو بگیر",
            "lead": "وقتی بازی می‌کنی و یه آپدیت یا تورنت پشت صحنه خط اینترنت رو پر می‌کنه، پینگ می‌پره. شب‌پا مصرف اینترنت هر برنامه رو نشون می‌ده و می‌تونی سقف سرعتش رو بذاری یا کلاً ببندیش. «محافظ موقع بازی» هم این کار رو خودکار انجام می‌ده.",
            "steps_h": "چطور پینگ بازی رو پایدار نگه دارم؟",
            "steps": ["از منوی کنار «پایداری پینگ» رو باز کن و پینگ زنده و نمودار پایداری رو ببین.", "توی لیست «چی اینترنتت رو می‌خوره» برنامه‌های پرمصرف رو پیدا کن.", "برای هر برنامه سقف دانلود و آپلود بذار (مگابیت یا مگابایت، هر کدوم که دوست داری) یا مسدودش کن.", "محافظ موقع بازی رو روشن کن تا وقتی بازی می‌کنی، سرعت بقیه‌ی برنامه‌ها خودکار محدود بشه و با بسته شدن بازی همه‌چی آزاد بشه."],
            "alt_line": "برای تغییر سریع DNS هم بخش «دی‌ان‌اس» هست؛ با تست پینگ چند سرور، حتی پشت فیلترشکن.",
            "feat_h": "چی تو این بخشه",
            "feats": ["پینگ زنده و نمودار پایداری", "مصرف اینترنت هر برنامه، سقف سرعت یا مسدودسازی", "محافظ موقع بازی: محدودیت خودکار بقیه‌ی برنامه‌ها تا وقتی بازی بازه", "تاریخچه‌ی مصرف و سهمیه‌ی ماهانه", "تغییر سریع DNS با ۱۱ سرور تازه؛ پشت فیلترشکن که همه‌ی پینگ‌ها الکی کم نشون داده می‌شه، شب‌پا گول نمی‌خوره و بهت می‌گه"],
            "faq": [("شب‌پا پینگ بازی رو کم می‌کنه؟", "شب‌پا مسیر اینترنت تا سرور بازی رو عوض نمی‌کنه. کارش اینه که برنامه‌های دیگه (آپدیت، تورنت، مرورگر) خط اینترنتت رو اشغال نکنن تا پینگ پایدار بمونه."), ("چرا آنتی‌ویروس بعضی وقت‌ها هشدار می‌ده؟", "برای سقف سرعت هر برنامه، شب‌پا از درایور متن‌باز WinDivert استفاده می‌کنه که چون یه ابزار شبکه‌ست، بعضی آنتی‌ویروس‌ها علامتش می‌زنن. اگه به این بخش نیاز نداری لازم نیست استفاده‌اش کنی.")],
        },
        "en": {
            "name": "Network and ping",
            "title": "Limit App Internet Speed and Keep Game Ping Stable | Shabpa",
            "desc": "See which app eats your internet and cap its speed. Shabpa's in-game protection automatically limits other apps while you play so your ping stays flat. Free.",
            "h1": "See what eats your internet, and stop it",
            "lead": "When you game and an update or a torrent quietly fills your line, your ping spikes. Shabpa shows each app's internet use and lets you cap its speed or block it altogether. In-game protection does it for you automatically.",
            "steps_h": "How do I keep my game ping stable?",
            "steps": ["Open \"Ping stability\" from the side menu and watch the live ping and the stability chart.", "In the \"what eats your internet\" list, find the heavy apps.", "Set a download and upload cap for each (in megabits or megabytes, whichever you prefer) or block it.", "Turn on in-game protection so other apps are capped automatically while you play, and released when the game closes."],
            "alt_line": "There is also a DNS page for switching DNS quickly, with a ping test across several servers, even behind a VPN.",
            "feat_h": "What is in this section",
            "feats": ["Live ping and a stability chart", "Per-app internet use, speed caps or blocking", "In-game protection: other apps are capped automatically while a game runs", "Usage history and a monthly allowance", "Quick DNS switcher with 11 more servers; behind a VPN, where every DNS looks falsely fast, Shabpa notices and tells you"],
            "faq": [("Does Shabpa lower my ping?", "Shabpa does not change the route to the game server. It keeps other apps (updates, torrents, browsers) from filling your line so your ping stays stable."), ("Why does my antivirus sometimes warn?", "For per-app speed caps Shabpa uses the open-source WinDivert driver, which some antivirus products flag because it is a network tool. If you do not need that feature, you do not have to use it.")],
        },
    },
    {
        "slug": "game-tuning", "img": "tuning", "alt": {"fa": "بهینه‌سازی بازی: ده تنظیم ویندوز با توضیح و برگشت کامل", "en": "Game tuning: ten Windows settings with explanations and full undo"},
        "fa": {
            "name": "بهینه‌سازی بازی",
            "title": "بهینه‌سازی ویندوز برای بازی، امن و قابل برگشت | شب‌پا",
            "desc": "ده تنظیم شناخته‌شده‌ی ویندوز برای بازی (اولویت پردازنده، Game Mode، HAGS و ...) با توضیح ساده و برگشت کامل. هیچ برنامه یا سرویسی حذف نمی‌شه. رایگان.",
            "h1": "ویندوزت رو برای بازی تنظیم کن، با برگشت کامل",
            "lead": "ابزارهای «بهینه‌ساز» معمولاً بی‌خبر چیزهایی رو تغییر می‌دن و برگشتشون سخته. بهینه‌سازی بازی شب‌پا فقط ده تنظیم مستند ویندوز رو عوض می‌کنه، هر کدوم رو با توضیح ساده نشون می‌ده، قبلش ازت می‌پرسه و مقدار خودت رو نگه می‌داره.",
            "steps_h": "چطور ویندوز رو برای بازی بهینه کنم؟",
            "steps": ["از منوی کنار «کنترل سیستم» و بعد تب «بهینه‌سازی بازی» رو باز کن.", "بین سه تب (پردازنده و رم، ویندوز و سیستم، گرافیک) بگرد و با ماوس روی علامت «i» کنار هر تنظیم برو تا ساده توضیح بده چیکار می‌کنه.", "هر تنظیمی که خواستی رو روشن کن. شب‌پا قبل از تغییر ازت تأیید می‌گیره و مقدار فعلی خودت رو ذخیره می‌کنه.", "هر وقت خواستی خاموشش کن تا دقیقاً همون مقدار قبلی برگرده، یا «برگردوندن همه به حالت قبل» رو بزن."],
            "alt_line": "بعضی تنظیم‌ها دسترسی ادمین می‌خوان و بعضی بعد از ری‌استارت اثر می‌کنن؛ کنار هر کدوم نوشته شده.",
            "feat_h": "چیزهایی که توش هست",
            "feats": ["اولویت پردازنده و زمان‌بندی برای بازی و سهم پس‌زمینه‌ی پردازنده", "حالت بازی خود ویندوز و خاموش‌کردن ضبط پنهان Game Bar", "زمان‌بندی گرافیک سخت‌افزاری (HAGS) و بیدار نگه داشتن خط PCIe", "تقویت بازی‌های پنجره‌ای و بدون‌کادر", "هیچ برنامه، سرویس یا فایلی حذف یا غیرفعال نمی‌شه"],
            "faq": [("بهینه‌سازی بازی شب‌پا امنه؟", "بله. فقط ده تنظیم مستند ویندوز رو عوض می‌کنه، قبلش می‌پرسه و با خاموش‌کردن هر تنظیم یا «برگردوندن همه»، دقیقاً مقدار قبلی خودت برمی‌گرده."), ("باعث بالا رفتن FPS می‌شه؟", "اثرش به سیستم و بازی بستگی داره و عدد خاصی وعده نمی‌دیم. هدفش اینه که ویندوز منابع رو بیشتر به بازی بده و کارهای پس‌زمینه کمتر مزاحم بشن.")],
        },
        "en": {
            "name": "Game tuning",
            "title": "Optimize Windows for Gaming, Safely and Reversibly | Shabpa",
            "desc": "Ten well-known Windows gaming settings (CPU priority, Game Mode, HAGS and more) with plain explanations and full undo. No program or service is removed. Free.",
            "h1": "Tune Windows for gaming, fully reversible",
            "lead": "Typical \"optimizers\" change things behind your back and are hard to undo. Shabpa's game tuning changes only ten documented Windows settings, explains each in plain words, asks first and keeps your own value.",
            "steps_h": "How do I optimize Windows for gaming?",
            "steps": ["Open \"System control\" from the side menu and then the \"Game tuning\" tab.", "Browse the three tabs (processor and memory, Windows and system, graphics) and hover the \"i\" next to a setting for a plain explanation.", "Switch on the settings you want. Shabpa asks before changing anything and saves your current value.", "Switch a setting off to put back exactly your previous value, or press \"put everything back\"."],
            "alt_line": "Some settings need administrator rights and some only take effect after a restart; each one says so.",
            "feat_h": "What is in it",
            "feats": ["Game processor priority, scheduling priority and the background share of the processor", "Windows' own Game Mode and stopping Game Bar's hidden recording", "Hardware-accelerated GPU scheduling (HAGS) and keeping the PCIe link awake", "A boost for windowed and borderless games", "No program, service or file is deleted or disabled"],
            "faq": [("Is Shabpa's game tuning safe?", "Yes. It changes only ten documented Windows settings, asks first, and switching a setting off (or \"put everything back\") restores your exact previous value."), ("Will it raise my FPS?", "That depends on your PC and the game, and we promise no specific number. The aim is for Windows to give more resources to the game and for background work to get in the way less.")],
        },
    },
    {
        "slug": "updates", "img": "updates", "alt": {"fa": "درایور کارت گرافیک و درایورهای پیشنهادی Windows Update", "en": "Graphics driver and Windows Update driver suggestions"},
        "fa": {
            "name": "به‌روزرسانی‌ها",
            "title": "به‌روزرسانی برنامه‌ها، درایور کارت گرافیک و آپدیت ویندوز | شب‌پا",
            "desc": "شب‌پا برنامه‌های قدیمی (با winget)، درایور کارت گرافیک و وضعیت آپدیت ویندوز رو بررسی می‌کنه و فقط با تأیید خودت به‌روزرسانی می‌کنه. رایگان و بدون اطلاعات شخصی.",
            "h1": "آپدیت برنامه‌ها، درایور کارت گرافیک و ویندوز؛ همه یکجا",
            "lead": "نسخه‌ی قدیمی برنامه‌ها و درایورها هم امنیت رو پایین میاره هم بازی‌ها رو بد اجرا می‌کنه. شب‌پا نشون می‌ده چی عقب مونده، ولی هیچ‌چیز رو بی‌اجازه‌ی تو نصب نمی‌کنه.",
            "steps_h": "چطور آپدیت برنامه‌ها و درایورها رو بررسی کنم؟",
            "steps": ["از منوی کنار «سلامت و امنیت» رو باز کن.", "تب «به‌روزرسانی برنامه‌ها» رو بزن و «بررسی به‌روزرسانی‌ها» رو انتخاب کن. شب‌پا از مدیر بسته‌ی خود ویندوز (winget) می‌پرسه کدوم برنامه نسخه‌ی جدیدتر داره.", "برنامه‌هایی که می‌خوای به‌روز بشن رو انتخاب و تأیید کن؛ از سایت خود سازنده دانلود و بررسی می‌شن.", "توی تب «درایورها» نسخه‌ی درایور کارت گرافیک رو می‌بینی و صفحه‌ی رسمی سازنده (AMD، NVIDIA یا Intel) رو باز می‌کنی. «جستجو» هم درایورهایی رو پیدا می‌کنه که Windows Update برای سخت‌افزارت تأیید کرده."],
            "alt_line": "وضعیت آپدیت ویندوز و سرویس‌ها هم توی تب «سلامت سیستم» همین بخش بررسی می‌شه.",
            "feat_h": "ویژگی‌ها",
            "feats": ["برنامه‌های قدیمی با winget؛ فقط نسخه‌هایی پیشنهاد می‌شن که با سیستمت سازگارن", "نصب فقط بعد از تأیید تو؛ ممکنه ویندوز برای بعضی‌ها تأیید ادمین بخواد و برنامه‌های بازشون بسته بشن", "نسخه‌ی نصب‌شده‌ی درایور کارت گرافیک و لینک صفحه‌ی رسمی سازنده", "درایورهای پیشنهادی Windows Update", "بررسی وضعیت آپدیت ویندوز و سرویس‌ها"],
            "faq": [("شب‌پا خودش برنامه‌ها رو آپدیت می‌کنه؟", "نه، بی‌اجازه‌ی تو هیچ‌چیز نصب نمی‌شه. شب‌پا فقط فهرست رو نشون می‌ده و بعد از انتخاب و تأیید تو، با winget از سایت سازنده نصب می‌کنه."), ("خود شب‌پا چطور آپدیت می‌شه؟", "برنامه نسخه‌ی جدید رو از چند منبع (گیت‌هاب، این سایت و میزبان ایرانی) می‌گیره، امضای دیجیتال فهرست به‌روزرسانی رو بررسی می‌کنه و فقط وقتی SHA-256 فایل با مقدار منتشرشده بخونه اجراش می‌کنه.")],
        },
        "en": {
            "name": "Updates",
            "title": "Update Apps, Graphics Drivers and Check Windows Update | Shabpa",
            "desc": "Shabpa checks outdated programs (through winget), your graphics driver and Windows Update status, and updates only with your approval. Free, no personal data.",
            "h1": "Update your apps, graphics driver and Windows in one place",
            "lead": "Old programs and drivers lower your security and make games run worse. Shabpa shows what is out of date, but never installs anything without your approval.",
            "steps_h": "How do I check for app and driver updates?",
            "steps": ["Open \"Health and security\" from the side menu.", "Choose the \"App updates\" tab and press \"Check for updates\". Shabpa asks Windows' own package manager (winget) which programs have a newer version.", "Select the programs you want to update and confirm; they are downloaded from the publisher and checked.", "In the \"Drivers\" tab you see your graphics driver version and open the maker's official page (AMD, NVIDIA or Intel). \"Search\" also finds drivers that Windows Update has approved for your hardware."],
            "alt_line": "Windows update and service status are checked in the \"System health\" tab of the same section.",
            "feat_h": "What you get",
            "feats": ["Outdated programs through winget; only versions that fit your PC are offered", "Installation only after you confirm; Windows may ask for administrator approval for some, and open programs may be closed", "Installed graphics driver version and a link to the maker's official page", "Driver suggestions from Windows Update", "A check of Windows update and service status"],
            "faq": [("Does Shabpa update my programs on its own?", "No, nothing is installed without your approval. Shabpa only shows the list and, after you choose and confirm, installs through winget from the publisher's site."), ("How does Shabpa update itself?", "The app fetches the new version from several sources (GitHub, this site and an Iranian host), checks the digital signature of the update manifest, and runs the file only if its SHA-256 matches the published value.")],
        },
    },
    {
        "slug": "night-light", "img": "comfort", "alt": {"fa": "کم‌نور کردن صفحه و رنگ گرم شب", "en": "Screen dimming and a warm night tint"},
        "fa": {
            "name": "نور شب",
            "title": "نور شب و کم‌نور کردن صفحه، حتی کمتر از حداقل مانیتور | شب‌پا",
            "desc": "با شب‌پا صفحه رو از حداقل نور خود مانیتور هم کم‌نورتر کن، رنگ گرم شب بذار و یادآور استراحت بگیر. رنگ گرم مثل نور شب خود ویندوز کار می‌کنه. رایگان.",
            "h1": "شب‌ها چشمت رو اذیت نکن؛ کم‌نورتر از حداقل مانیتور",
            "lead": "بعضی مانیتورها حتی روی حداقل نور هم شب‌ها زیادی روشنن. شب‌پا صفحه رو از حداقل خود مانیتور هم کم‌نورتر می‌کنه و رنگ گرم شب رو مثل نور شب ویندوز اعمال می‌کنه، بی‌اینکه تصویر زرد-خاکستری بشه.",
            "steps_h": "چطور صفحه رو کم‌نورتر از حداقل کنم؟",
            "steps": ["از منوی کنار «نور شب و استراحت» رو باز کن.", "کم‌نوری رو روشن کن و با لغزنده میزان تیرگی رو بذار؛ پایین‌تر از حداقل مانیتور هم می‌ره.", "رنگ گرم شب رو با یکی از پیش‌تنظیم‌های دمای رنگ (کلوین) روشن کن و در صورت نیاز تغییرش بده.", "بازه‌ی شب رو تنظیم کن تا کم‌نوری هر شب خودکار شروع بشه. با میانبر صفحه‌کلید هم می‌تونی روشن/خاموش و تیره‌تر/روشن‌تر کنی."],
            "alt_line": "برای شب‌هایی که دیر می‌خوابی، حالت شب‌خواب و یادآور استراحت هم هست.",
            "feat_h": "امکانات",
            "feats": ["نور شب با دمای رنگ قابل‌تنظیم", "کم‌نور شدن خودکار توی بازه‌ی شب", "میانبر صفحه‌کلید برای روشن/خاموش و تیره‌تر/روشن‌تر", "یادآور استراحت و حالت شب‌خواب", "تست سطح صدای میکروفون"],
            "faq": [("با نور شب خود ویندوز چه فرقی داره؟", "نور شب ویندوز فقط رنگ رو گرم می‌کنه. شب‌پا علاوه بر رنگ گرم می‌تونه صفحه رو از حداقل نور خود مانیتور هم تیره‌تر کنه، و رنگ گرمش مثل نور شب ویندوز کار می‌کنه و تصویر رو زرد-خاکستری نمی‌کنه."), ("به مانیتورم آسیب می‌زنه؟", "نه. تیرگی و رنگ روی خروجی تصویر اعمال می‌شه و تنظیمات سخت‌افزاری مانیتور رو عوض نمی‌کنه؛ با خاموش کردن یا بستن برنامه همه‌چی برمی‌گرده.")],
        },
        "en": {
            "name": "Night light",
            "title": "Night Light and Screen Dimmer Below Your Monitor's Minimum | Shabpa",
            "desc": "Dim your screen below your monitor's own minimum, add a warm night tint and get break reminders with Shabpa. The warm tint works like Windows' Night Light. Free.",
            "h1": "Go easy on your eyes at night, dimmer than your monitor allows",
            "lead": "Some monitors are too bright at night even on their lowest setting. Shabpa dims the screen below the monitor's own minimum and applies a warm night tint the way Windows' Night Light does, without turning the picture yellow-grey.",
            "steps_h": "How do I dim the screen below the minimum?",
            "steps": ["Open \"Night light and rest\" from the side menu.", "Switch dimming on and set the darkness with the slider; it goes below the monitor's minimum.", "Turn on the warm night tint with one of the color-temperature (Kelvin) presets and adjust it if you like.", "Set your night hours so dimming starts automatically every evening. Keyboard shortcuts also toggle it and dim or brighten."],
            "alt_line": "For late nights there is also a sleep mode and break reminders.",
            "feat_h": "What you get",
            "feats": ["Night light with adjustable color temperature", "Auto-dim during your night hours", "Keyboard shortcuts to toggle and to dim or brighten", "Break reminders and sleep mode", "A microphone level test"],
            "faq": [("How is it different from Windows' Night Light?", "Windows' Night Light only warms the color. Shabpa can also dim the screen below the monitor's own minimum, and its warm tint works like Windows' Night Light and never turns the picture yellow-grey."), ("Can it damage my monitor?", "No. Darkness and tint are applied to the picture output and never change the monitor's hardware settings; closing or switching off the app puts everything back.")],
        },
    },
    {
        "slug": "backup-cleanup", "img": "backup", "alt": {"fa": "تحلیل فضای دیسک: بزرگ‌ترین فایل‌ها و پوشه‌ها", "en": "Disk space analysis: biggest files and folders"},
        "fa": {
            "name": "پشتیبان و پاکسازی",
            "title": "پشتیبان‌گیری از پوشه‌ها، فایل تکراری و پاکسازی ویندوز | شب‌پا",
            "desc": "پشتیبان‌گیری زمان‌بندی‌شده با بررسی درستی نسخه‌ها، پیدا کردن فایل‌های تکراری، تحلیل فضای دیسک و پاکسازی فایل‌های موقت با شب‌پا. هر چی حذف بشه به سطل بازیافت می‌ره.",
            "h1": "پوشه‌هات امن، دیسکت سبک",
            "lead": "شب‌پا از پوشه‌هایی که انتخاب می‌کنی طبق برنامه پشتیبان می‌گیره و درستی نسخه‌ها رو بررسی می‌کنه. جاهایی که فضا رو می‌خورن و فایل‌های تکراری رو هم نشونت می‌ده؛ بدون اینکه چیزی بی‌خبر حذف بشه.",
            "steps_h": "چطور از پوشه‌ها پشتیبان بگیرم و دیسک رو سبک کنم؟",
            "steps": ["از منوی کنار «فایل و پشتیبان» رو باز کن.", "توی تب پشتیبان، پوشه‌ها و مقصد رو انتخاب کن و زمان‌بندی بذار. نسخه‌ها بعد از ساخته شدن بررسی می‌شن.", "با «تحلیل فضا» بزرگ‌ترین فایل‌ها و پوشه‌ها رو ببین و با «فایل‌های تکراری» نسخه‌های اضافه رو پیدا کن.", "با «پاک‌سازی» فایل‌های موقت و کش رو ببین؛ حجم قبل از حذف نشون داده می‌شه و تأیید می‌گیره."],
            "alt_line": "بازیابی هیچ‌وقت فایل فعلی‌ت رو جایگزین نمی‌کنه.",
            "feat_h": "ایمنی",
            "feats": ["پشتیبان زمان‌بندی‌شده با بررسی درستی نسخه‌ها", "بازیابی که فایل فعلی رو جایگزین نمی‌کنه", "هر چیزی که حذف می‌شه فقط به سطل بازیافت می‌ره، بعد از پیش‌نمایش و فقط از پوشه‌ای که اسکن کردی", "پاک‌سازی فقط به پوشه‌های موقت و کش دست می‌زنه"],
            "faq": [("شب‌پا فایل‌هام رو پاک می‌کنه؟", "فقط بعد از پیش‌نمایش و تأیید تو، و فقط به سطل بازیافت. فایل‌ها برای همیشه پاک نمی‌شن و کار فقط توی پوشه‌ای انجام می‌شه که خودت اسکن کردی."), ("پاک‌سازی فایل‌های موقت امنه؟", "بله. فقط پوشه‌های موقت و کش رو پاک می‌کنه، حجم قابل‌آزادسازی رو قبل از حذف نشون می‌ده و تأیید می‌گیره.")],
        },
        "en": {
            "name": "Backup and clean-up",
            "title": "Folder Backup, Duplicate Finder and Windows Clean-up | Shabpa",
            "desc": "Scheduled folder backups with verification, a duplicate file finder, disk space analysis and temp-file clean-up with Shabpa. Anything deleted goes to the Recycle Bin.",
            "h1": "Folders safe, disk light",
            "lead": "Shabpa backs up the folders you choose on a schedule and verifies the copies. It also shows what eats your disk and finds duplicate files, without deleting anything behind your back.",
            "steps_h": "How do I back up folders and free up disk space?",
            "steps": ["Open \"Files and backup\" from the side menu.", "On the backup tab choose the folders and the destination and set a schedule. Copies are verified once they are made.", "Use \"Space analysis\" to see the biggest files and folders and \"Duplicates\" to find extra copies.", "Use \"Clean-up\" to see temp and cache files; the size is shown before deleting and it asks for confirmation."],
            "alt_line": "Restore never overwrites your current files.",
            "feat_h": "Safety",
            "feats": ["Scheduled backup with verification of the copies", "A restore that never overwrites current files", "Anything deleted goes to the Recycle Bin only, after a preview and only from the folder you scanned", "Clean-up touches temporary and cache folders only"],
            "faq": [("Does Shabpa delete my files?", "Only after a preview and your confirmation, and only to the Recycle Bin. Files are not erased for good, and work happens only in the folder you scanned."), ("Is cleaning temp files safe?", "Yes. It only cleans temporary and cache folders, shows how much it will free before deleting and asks for confirmation.")],
        },
    },
    {
        "slug": "health-check", "img": "health", "alt": {"fa": "سلامت و امنیت: امتیاز سلامت سیستم و وضعیت دیسک‌ها", "en": "Health and security: system health score and drive status"},
        "fa": {
            "name": "سلامت سیستم",
            "title": "بررسی سلامت ویندوز و دیدن خطاهای پنهان سیستم | شب‌پا",
            "desc": "شب‌پا خطاهای پنهانی که ویندوز پشت صحنه ثبت می‌کنه رو به زبون ساده نشون می‌ده؛ همراه با بررسی دیسک، فایروال، دیفندر، UAC و برنامه‌های اجرای خودکار. رایگان.",
            "h1": "حال سیستمت رو بدون اصطلاح پیچیده بدون",
            "lead": "ویندوز مدام خطاهایی رو پشت صحنه ثبت می‌کنه که هیچ‌جا نشونت نمی‌ده و فقط توی Event Viewer با کدهای عجیب پیدا می‌شن. شب‌پا اون‌ها رو گروه‌بندی و به زبون ساده توضیح می‌ده و می‌گه معمولاً یعنی چی و چیکار کنی.",
            "steps_h": "چطور خطاهای پنهان ویندوز رو ببینم؟",
            "steps": ["از منوی کنار «سلامت و امنیت» رو باز کن و تب «سلامت سیستم» رو بزن.", "شمارنده‌ی خطاهای ۷ روز اخیر رو ببین و روی هر گروه خطا بزن.", "توضیح ساده می‌آد: ویندوز دقیقاً چی نوشته، کی بوده و معمولاً یعنی چی.", "خطاهایی که بعد از آخرین روشن‌شدن ویندوز تکرار نشدن یا خودت «رفع شد» زدی کنار گذاشته می‌شن؛ اگه دوباره اتفاق بیفتن برمی‌گردن."],
            "alt_line": "برای فرستادن مشکل به پشتیبانی، تب «گزارش» یه گزارش بدون اطلاعات شخصی می‌سازه.",
            "feat_h": "چی بررسی می‌شه",
            "feats": ["دیسک، به‌روزرسانی ویندوز و سرویس‌ها", "وضعیت فایروال، دیفندر و UAC", "نظارت بر برنامه‌های اجرای خودکار", "خطاهای پنهان ویندوز با توضیح ساده", "گزارش بدون اطلاعات شخصی، آماده‌ی فرستادن"],
            "faq": [("آیا شب‌پا اطلاعات سیستمم رو جایی می‌فرسته؟", "نه. بررسی‌ها روی خود کامپیوتر انجام می‌شه و گزارش فقط وقتی ساخته می‌شه که خودت بخوای؛ اطلاعات شخصی از اون حذف شده."), ("خطای ویندوز یعنی سیستمم خرابه؟", "لزوماً نه. ویندوز خیلی چیزهای بی‌اهمیت رو هم ثبت می‌کنه. شب‌پا کمک می‌کنه ببینی کدوم‌ها مهمن و کدوم‌ها معمولی‌ان.")],
        },
        "en": {
            "name": "System health",
            "title": "Check Windows Health and See Hidden System Errors | Shabpa",
            "desc": "Shabpa shows the hidden errors Windows logs behind the scenes in plain language, plus checks for disk, firewall, Defender, UAC and startup programs. Free.",
            "h1": "Your system's health, in plain language",
            "lead": "Windows constantly logs errors behind the scenes that it never shows you and that only turn up in Event Viewer with cryptic codes. Shabpa groups them, explains them in plain words and tells you what they usually mean and what to do.",
            "steps_h": "How do I see the hidden Windows errors?",
            "steps": ["Open \"Health and security\" from the side menu and choose the \"System health\" tab.", "Look at the 7-day error counter and click an error group.", "A plain explanation appears: what Windows wrote, when, and what it usually means.", "Errors that did not come back since Windows last started, or that you marked \"fixed\", are set aside; they return if they happen again."],
            "alt_line": "To send a problem to support, the \"Report\" tab builds a report with personal details removed.",
            "feat_h": "What is checked",
            "feats": ["Disk, Windows updates and services", "Firewall, Defender and UAC status", "A watch on startup programs", "Hidden Windows errors with plain explanations", "A report with no personal data, ready to send"],
            "faq": [("Does Shabpa send my system data anywhere?", "No. Checks run on your own PC and a report is only built when you ask for it, with personal details removed."), ("Does a Windows error mean my PC is broken?", "Not necessarily. Windows logs many harmless things too. Shabpa helps you see which ones matter and which are routine.")],
        },
    },
]

UI = {
    "fa": {"dir": "rtl", "home": "خانه", "features": "امکانات", "dl": "دانلود", "other": "English", "other_title": "View this page in English", "path": "/",
           "guides": "راهنماهای شب‌پا", "faq": "سوالات پرتکرار", "related": "بخش‌های دیگه‌ی شب‌پا", "cta_h": "شب‌پا رو رایگان بگیر", "cta_p": "رایگان و متن‌باز، برای ویندوز ۱۰ و ۱۱. SHA-256 هر نسخه کنار دانلود منتشر می‌شه.",
           "cta": "دانلود شب‌پا", "locale": "fa_IR", "alt_locale": "en_US", "site": "شب‌پا", "skip": "رفتن به محتوا", "nav": "منوی اصلی", "crumb_nav": "مسیر صفحه",
           "copy": "© ۱۴۰۵ شب‌پا. کلیه‌ی حقوق این وب‌سایت (متن، تصاویر و طراحی) محفوظ است. نرم‌افزار شب‌پا تحت مجوز متن‌باز MIT منتشر شده و استفاده از آن آزاده.", "foot": "شب‌پا · ساخته‌ی", "lic": "مجوز MIT", "gh": "گیت‌هاب", "sec": "امنیت", "chg": "تغییرات", "pol": "سیاست امضا"},
    "en": {"dir": "ltr", "home": "Home", "features": "Features", "dl": "Download", "other": "فارسی", "other_title": "مشاهده‌ی این صفحه به فارسی", "path": "/en/",
           "guides": "Shabpa guides", "faq": "Frequently asked questions", "related": "More from Shabpa", "cta_h": "Get Shabpa for free", "cta_p": "Free and open source, for Windows 10 and 11. The SHA-256 of every version is published next to the download.",
           "cta": "Download Shabpa", "locale": "en_US", "alt_locale": "fa_IR", "site": "Shabpa", "skip": "Skip to content", "nav": "Main menu", "crumb_nav": "Breadcrumb",
           "copy": "© 2026 Shabpa. All rights to this website (text, images and design) are reserved. The Shabpa software itself is released under the open-source MIT license.", "foot": "Shabpa · made by", "lic": "MIT license", "gh": "GitHub", "sec": "Security", "chg": "Changelog", "pol": "Signing policy"},
}


def url(lang, slug):
    return f"{SITE}/{'en/' if lang == 'en' else ''}{slug}/"


def jsonld(lang, p):
    c, u = p[lang], UI[lang]
    me = url(lang, p["slug"])
    home = SITE + u["path"]
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": me + "#page", "url": me, "name": c["title"], "description": c["desc"], "inLanguage": lang, "isPartOf": {"@id": SITE + "/#site"},
         "about": {"@id": (SITE + "/en/#app") if lang == "en" else (SITE + "/#app")}, "dateModified": LASTMOD,
         "primaryImageOfPage": {"@type": "ImageObject", "url": SITE + ("/assets/img/en/" if lang == "en" else "/assets/img/") + p["img"] + ".webp"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": u["site"], "item": home},
            {"@type": "ListItem", "position": 2, "name": c["name"], "item": me}]},
        {"@type": "FAQPage", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in c["faq"]]},
    ]}


def render(lang, p):
    c, u = p[lang], UI[lang]
    other = "en" if lang == "fa" else "fa"
    me, alt = url(lang, p["slug"]), url(other, p["slug"])
    fa_url, en_url = url("fa", p["slug"]), url("en", p["slug"])
    imgdir = "/assets/img/en/" if lang == "en" else "/assets/img/"
    img = imgdir + p["img"] + ".webp"
    og_img = SITE + "/assets/img/og.png"
    related = "".join(f'<a href="/{"en/" if lang == "en" else ""}{o["slug"]}/">{e(o[lang]["name"])}</a>' for o in PAGES if o is not p)
    steps = "".join(f"<li>{e(s)}</li>" for s in c["steps"])
    feats = "".join(f"<li>{e(f)}</li>" for f in c["feats"])
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in c["faq"])
    ld = json.dumps(jsonld(lang, p), ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{lang}" dir="{u['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(c['title'])}</title>
<meta name="description" content="{e(c['desc'], quote=True)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="author" content="Mr.PitPot">
<meta name="theme-color" content="#04061a">
<meta name="color-scheme" content="dark">
<link rel="canonical" href="{me}">
<link rel="alternate" hreflang="fa" href="{fa_url}">
<link rel="alternate" hreflang="en" href="{en_url}">
<link rel="alternate" hreflang="x-default" href="{fa_url}">
<link rel="icon" href="/assets/img/logo.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/img/logo.png">
<link rel="preload" href="/assets/fonts/Vazirmatn-Medium.woff2" as="font" type="font/woff2" crossorigin>
<meta property="og:type" content="article">
<meta property="og:locale" content="{u['locale']}">
<meta property="og:locale:alternate" content="{u['alt_locale']}">
<meta property="og:site_name" content="{u['site']}">
<meta property="og:title" content="{e(c['title'], quote=True)}">
<meta property="og:description" content="{e(c['desc'], quote=True)}">
<meta property="og:url" content="{me}">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(c['title'], quote=True)}">
<meta name="twitter:description" content="{e(c['desc'], quote=True)}">
<meta name="twitter:image" content="{og_img}">
<script type="application/ld+json">{ld}</script>
<link rel="stylesheet" href="/assets/style.css?v={CSS_V}">
</head>
<body class="night page404 doc">
<a class="skip" href="#main">{u['skip']}</a>
<div class="sky" aria-hidden="true"><div class="sky-grad"></div></div>
<header class="top">
  <a class="brand" href="{u['path']}" aria-label="{u['site']}"><img src="/assets/img/logo.png" width="38" height="38" alt=""><span>{u['site']}</span></a>
  <nav aria-label="{u['nav']}">
    <a href="{u['path']}#features">{u['features']}</a>
    <a href="{u['path']}#faq">{u['faq'] if lang == 'en' else 'سوالات'}</a>
  </nav>
  <a class="lang" href="{alt.replace(SITE, '')}" hreflang="{other}" lang="{other}" title="{u['other_title']}">{u['other']}</a>
  <a class="btn btn-sm" href="{u['path']}#download">{u['dl']}</a>
</header>
<main id="main">
  <nav class="crumbs" aria-label="{u['crumb_nav']}"><a href="{u['path']}">{u['site']}</a> / <span>{e(c['name'])}</span></nav>
  <header class="card text doc-hero">
    <h1>{e(c['h1'])}</h1>
    <p class="lead">{e(c['lead'])}</p>
    <p><a class="btn" href="{u['path']}#download">{u['cta']}</a></p>
  </header>
  <figure class="shot"><div class="win win-app"><img src="{img}" width="1280" height="800" alt="{e(p['alt'][lang], quote=True)}" fetchpriority="high"></div></figure>
  <section class="card text">
    <h2>{e(c['steps_h'])}</h2>
    <ol class="steps">{steps}</ol>
    <p class="aside">{e(c['alt_line'])}</p>
  </section>
  <section class="card text">
    <h2>{e(c['feat_h'])}</h2>
    <ul class="opts">{feats}</ul>
  </section>
  <section class="card text faq-doc">
    <h2>{u['faq']}</h2>
    {faq}
  </section>
  <section class="card text cta-card">
    <h2>{u['cta_h']}</h2>
    <p>{u['cta_p']}</p>
    <p><a class="btn btn-lg" href="{u['path']}#download">{u['cta']}</a></p>
    <h3>{u['related']}</h3>
    <div class="related">{related}</div>
  </section>
</main>
<footer class="foot">
  <div><img src="/assets/img/logo.png" width="28" height="28" alt=""><span>{u['foot']} <a href="https://github.com/MrPitPot" rel="noopener">Mr.PitPot</a> · {u['lic']}</span></div>
  <nav aria-label="Links">
    <a href="https://github.com/MrPitPot/shabpa" rel="noopener">{u['gh']}</a>
    <a href="https://github.com/MrPitPot/shabpa/blob/main/SECURITY.md" rel="noopener">{u['sec']}</a>
    <a href="{u['path']}changelog/">{u['chg']}</a>
  </nav>
  <p class="legal">{u['copy']}</p>
</footer>
</body>
</html>
"""


# ---- changelog page -------------------------------------------------------------------------------------------------------------------------------------------
# Short, tidy notes per version (a few emoji bullets): the patch notes kept next to CHANGELOG.md in the app repo (patch-note-<v>.fa.md and .en.md). CHANGELOG.md gives the order and the dates.
# A version without both notes is left out: the technical entry in CHANGELOG.md is not meant for visitors.
CHANGELOG_TEXT = {
    "fa": {"name": "تغییرات نسخه‌ها", "title": "تغییرات نسخه‌ها | شب‌پا", "desc": "فهرست کوتاه و ساده‌ی تغییرات هر نسخه‌ی شب‌پا: چی تازه شده و چی درست شده.", "h1": "تغییرات نسخه‌ها",
           "lead": "هر نسخه‌ی شب‌پا چی تازه داشت و چی درست شد؛ کوتاه و بی‌پیچیدگی. فهرست کامل و فنی توی گیت‌هاب هست."},
    "en": {"name": "Changelog", "title": "Changelog | Shabpa", "desc": "A short, plain list of what changed in every Shabpa version: what is new and what was fixed.", "h1": "Changelog",
           "lead": "What every Shabpa version added and fixed, short and plain. The full technical list is on GitHub."},
}


def load_notes(path):
    """A patch note as (heading, [bullets]) groups. The title line is dropped; a heading is a line without a bullet."""
    groups, cur = [], None
    for raw in open(path, encoding="utf-8").read().splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("\u2022"):
            if cur is not None:
                cur[1].append(line.lstrip("\u2022 ").strip())
            continue
        cur = [line, []]
        groups.append(cur)
    return [(h, b) for h, b in groups if b]


def versions():
    """(version, date, {fa: groups, en: groups}) newest first, only where both notes exist."""
    out = []
    if not APP:
        return out
    for m in re.finditer(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})", open(os.path.join(APP, "CHANGELOG.md"), encoding="utf-8").read(), re.M):
        v, d = m.groups()
        fa, en = (os.path.join(APP, f"patch-note-{v}.{l}.md") for l in ("fa", "en"))
        if os.path.exists(fa) and os.path.exists(en):
            out.append((v, d, {"fa": load_notes(fa), "en": load_notes(en)}))
    return out


def render_changelog(lang):
    c, u = CHANGELOG_TEXT[lang], UI[lang]
    other = "en" if lang == "fa" else "fa"
    me, alt = SITE + u["path"] + "changelog/", SITE + UI[other]["path"] + "changelog/"
    fa_url, en_url = SITE + "/changelog/", SITE + "/en/changelog/"
    cards = []
    for v, d, notes in versions():
        body = "".join(f"<h3>{e(heading)}</h3><ul class=\"opts\">" + "".join(f"<li>{e(b)}</li>" for b in bullets) + "</ul>" for heading, bullets in notes[lang])
        shown = d if lang == "en" else re.sub(r"\d", lambda m: "۰۱۲۳۴۵۶۷۸۹"[int(m.group())], d)
        vs = v if lang == "en" else re.sub(r"\d", lambda m: "۰۱۲۳۴۵۶۷۸۹"[int(m.group())], v)
        cards.append(f'  <section class="card text" id="v{v}">\n    <h2><span dir="ltr">{vs}</span> <small>· <time datetime="{d}">{shown}</time></small></h2>\n    {body}\n  </section>')
    ld = json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": me + "#page", "url": me, "name": c["title"], "description": c["desc"], "inLanguage": lang, "isPartOf": {"@id": SITE + "/#site"}, "dateModified": LASTMOD},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": u["site"], "item": SITE + u["path"]}, {"@type": "ListItem", "position": 2, "name": c["name"], "item": me}]}]},
        ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{lang}" dir="{u['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(c['title'])}</title>
<meta name="description" content="{e(c['desc'], quote=True)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="author" content="Mr.PitPot">
<meta name="theme-color" content="#04061a">
<meta name="color-scheme" content="dark">
<link rel="canonical" href="{me}">
<link rel="alternate" hreflang="fa" href="{fa_url}">
<link rel="alternate" hreflang="en" href="{en_url}">
<link rel="alternate" hreflang="x-default" href="{fa_url}">
<link rel="icon" href="/assets/img/logo.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/img/logo.png">
<link rel="preload" href="/assets/fonts/Vazirmatn-Medium.woff2" as="font" type="font/woff2" crossorigin>
<meta property="og:type" content="website">
<meta property="og:locale" content="{u['locale']}">
<meta property="og:site_name" content="{u['site']}">
<meta property="og:title" content="{e(c['title'], quote=True)}">
<meta property="og:description" content="{e(c['desc'], quote=True)}">
<meta property="og:url" content="{me}">
<meta property="og:image" content="{SITE}/assets/img/og.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld}</script>
<link rel="stylesheet" href="/assets/style.css?v={CSS_V}">
</head>
<body class="night page404 doc">
<a class="skip" href="#main">{u['skip']}</a>
<div class="sky" aria-hidden="true"><div class="sky-grad"></div></div>
<header class="top">
  <a class="brand" href="{u['path']}" aria-label="{u['site']}"><img src="/assets/img/logo.png" width="38" height="38" alt=""><span>{u['site']}</span></a>
  <nav aria-label="{u['nav']}">
    <a href="{u['path']}#features">{u['features']}</a>
    <a href="{u['path']}#faq">{u['faq'] if lang == 'en' else 'سوالات'}</a>
  </nav>
  <a class="lang" href="{alt.replace(SITE, '')}" hreflang="{other}" lang="{other}" title="{u['other_title']}">{u['other']}</a>
  <a class="btn btn-sm" href="{u['path']}#download">{u['dl']}</a>
</header>
<main id="main">
  <nav class="crumbs" aria-label="{u['crumb_nav']}"><a href="{u['path']}">{u['site']}</a> / <span>{e(c['name'])}</span></nav>
  <header class="card text doc-hero">
    <h1>{e(c['h1'])}</h1>
    <p class="lead">{e(c['lead'])} <a href="https://github.com/MrPitPot/shabpa/blob/main/CHANGELOG.md" rel="noopener">CHANGELOG.md</a></p>
  </header>
{chr(10).join(cards)}
</main>
<footer class="foot">
  <div><img src="/assets/img/logo.png" width="28" height="28" alt=""><span>{u['foot']} <a href="https://github.com/MrPitPot" rel="noopener">Mr.PitPot</a> · {u['lic']}</span></div>
  <nav aria-label="Links">
    <a href="https://github.com/MrPitPot/shabpa" rel="noopener">{u['gh']}</a>
    <a href="https://github.com/MrPitPot/shabpa/blob/main/SECURITY.md" rel="noopener">{u['sec']}</a>
    <a href="{u['path']}changelog/">{u['chg']}</a>
  </nav>
  <p class="legal">{u['copy']}</p>
</footer>
</body>
</html>
"""


def guides_block(lang):
    u = UI[lang]
    items = "".join(
        f'<a class="guide" href="/{"en/" if lang == "en" else ""}{p["slug"]}/"><b>{e(p[lang]["name"])}</b><span>{e(p[lang]["h1"])}</span></a>' for p in PAGES)
    return f'<!--guides-->\n<section class="guides" id="guides" data-title="{e(u["guides"], quote=True)}">\n  <div class="card text wide">\n    <h2>{u["guides"]}</h2>\n    <div class="guide-grid">{items}</div>\n  </div>\n</section>\n<!--/guides-->'


def strip(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t))).strip()


def refresh_home_ld(s, lang):
    """Keeps the FAQPage in the home page's JSON-LD equal to the visible FAQ, and the brand spellings in sync."""
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    d = json.loads(m.group(1))
    items = re.findall(r"<details><summary>(.*?)</summary>\s*<p>(.*?)</p></details>", s, re.S)
    for node in d["@graph"]:
        if node["@type"] == "FAQPage":
            node["mainEntity"] = [{"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in items]
        if node["@type"] == "SoftwareApplication":
            node["alternateName"] = ["Shabpa", "شب‌پا", "شب پا", "شبپا"]
        if node["@type"] == "WebSite":
            node["alternateName"] = ["Shabpa", "شب پا", "شبپا"] if lang == "fa" else ["شب‌پا", "شب پا"]
    tag = '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False, indent=1).replace("</", "<\\/") + "</script>"
    return s[:m.start()] + tag + s[m.end():]


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    if versions():
        write(os.path.join(ROOT, "changelog", "index.html"), render_changelog("fa"))
        write(os.path.join(ROOT, "en", "changelog", "index.html"), render_changelog("en"))
    for p in PAGES:
        write(os.path.join(ROOT, p["slug"], "index.html"), render("fa", p))
        write(os.path.join(ROOT, "en", p["slug"], "index.html"), render("en", p))
    # the guide list on both home pages
    for rel, lang in (("index.html", "fa"), ("en/index.html", "en")):
        path = os.path.join(ROOT, rel)
        s = open(path, encoding="utf-8").read()
        block = guides_block(lang)
        if "<!--guides-->" in s:
            s = re.sub(r"<!--guides-->.*?<!--/guides-->", lambda m: block, s, flags=re.S)
        else:
            marker = '<section class="download"'
            assert marker in s
            s = s.replace(marker, block + "\n\n" + marker, 1)
        s = refresh_home_ld(s, lang)
        s = s.replace("assets/style.css?v=20261022e", "assets/style.css?v=" + CSS_V)
        write(path, s)
    # sitemap
    rows = []

    def entry(fa_u, en_u, loc, prio, imgs=()):
        im = "".join(f"<image:image><image:loc>{i}</image:loc></image:image>" for i in imgs)
        return (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{LASTMOD}</lastmod>\n    <priority>{prio}</priority>\n"
                f'    <xhtml:link rel="alternate" hreflang="fa" href="{fa_u}"/>\n    <xhtml:link rel="alternate" hreflang="en" href="{en_u}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{fa_u}"/>\n' + (f"    {im}\n" if im else "") + "  </url>")

    rows.append(entry(SITE + "/", SITE + "/en/", SITE + "/", "1.0", [SITE + "/assets/img/home.webp", SITE + "/assets/img/tuning.webp", SITE + "/assets/img/assistant.webp"]))
    rows.append(entry(SITE + "/", SITE + "/en/", SITE + "/en/", "0.9", [SITE + "/assets/img/en/home.webp", SITE + "/assets/img/en/tuning.webp", SITE + "/assets/img/en/assistant.webp"]))
    for p in PAGES:
        rows.append(entry(url("fa", p["slug"]), url("en", p["slug"]), url("fa", p["slug"]), "0.8", [SITE + "/assets/img/" + p["img"] + ".webp"]))
        rows.append(entry(url("fa", p["slug"]), url("en", p["slug"]), url("en", p["slug"]), "0.7", [SITE + "/assets/img/en/" + p["img"] + ".webp"]))
    if versions():
        rows.append(entry(SITE + "/changelog/", SITE + "/en/changelog/", SITE + "/changelog/", "0.5"))
        rows.append(entry(SITE + "/changelog/", SITE + "/en/changelog/", SITE + "/en/changelog/", "0.4"))
    write(os.path.join(ROOT, "sitemap.xml"),
          '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
          + "\n".join(rows) + "\n</urlset>\n")
    print("pages:", len(PAGES) * 2, "changelog versions:", len(versions()))


if __name__ == "__main__":
    sys.exit(main())
