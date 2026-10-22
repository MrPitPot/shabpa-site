# راه‌اندازی و امنیت سایت ShabPa.ir

## وضعیت فعلی (دیپلوی‌شده)
- **دانلود از خود دامنه** (برای کاربرایی که GitHub براشون کند/بسته‌ست): `src/worker.js` مسیر `/api/latest` (اطلاعات نسخه) و `/download/ShabpaSetup.exe` رو می‌ده. فایل از ریلیز رسمی GitHub گرفته می‌شه، SHA-256 اش با digest منتشرشده‌ی GitHub چک می‌شه و بعد توی کش لبه‌ی Cloudflare می‌مونه (ادامه‌ی دانلود/Range پشتیبانی می‌شه). اگه چک SHA جور نباشه یا GitHub جواب نده، کاربر به GitHub هدایت می‌شه. نسخه‌ی جدید خودکار برمی‌داره (نیازی به دیپلوی دوباره نیست؛ تا ~۱۰ دقیقه بعد از انتشار ریلیز).
- **آمار**: علاوه بر Web Analytics، Worker برای هر بازدید صفحه‌ی اصلی و هر دانلود یه لاگ بدون IP می‌نویسه (`evt`: view/download، نسخه، کشور). توی داشبورد Cloudflare ← Workers & Pages ← shabpa ← Logs دیده می‌شه (فیلتر `evt = download`).
- **سبک‌سازی**: `html.lite` برای دستگاه کم‌توان/اینترنت کند/صرفه‌جویی داده خودکار فعال می‌شه (`?lite=1` و `?lite=0` برای تست دستی).
- دو زبانه: فارسی در `public/index.html` (آدرس `/`) و انگلیسی در `public/en/index.html` (آدرس `/en/`) با عکس‌های رابط انگلیسی در `public/assets/img/en/`. هر تغییر متن باید توی هر دو فایل انجام بشه. دکمه‌ی زبان و پیشنهاد یک‌باره‌ی زبان توی `main.js` (بخش «زبان»).
- ریپو: <https://github.com/MrPitPot/shabpa-site>؛ سایت همون پوشه‌ی `public/` هست.
- هاست: Cloudflare (Workers با static assets، همون Pages جدید)، پروژه‌ی `shabpa`. دیپلوی: `npx wrangler deploy` از ریشه‌ی ریپو.
- دامنه‌ها: `shabpa.ir` و `www.shabpa.ir` به‌عنوان custom domain وصل شدن. آدرس workers.dev خاموشه.
- آمار بازدید: Cloudflare Web Analytics (بدون کوکی، آدرسش توی CSP مجازه). دانلودها رو از GitHub بشمار: `gh api repos/MrPitPot/shabpa/releases --jq ".[]|[.tag_name,(.assets[]|select(.name==\"ShabpaSetup.exe\")|.download_count)]"`.
- ریدایرکت http به https و www به shabpa.ir توسط `src/worker.js` انجام می‌شه (نه تنظیمات داشبورد). HSTS ساده‌ست (یک سال، بدون preload و includeSubDomains) تا بعداً مشکلی برای زیردامنه‌ها نسازه.
- کارهای دستی باقی‌مونده توی داشبورد Cloudflare: Web Analytics خودکار رو خاموش کن (CSP بلاکش می‌کنه و با ادعای «بدون ردیابی» هم جوره)؛ DNSSEC و ورود دومرحله‌ای رو روشن کن.

سایت کاملاً استاتیکه (HTML/CSS/JS)، یعنی سرور، دیتابیس و پنل ادمینی وجود نداره که هک بشه. سطح حمله فقط حساب‌ها و DNS هست.

## ۱. هاست (پیشنهاد: Cloudflare Pages، رایگان)
1. یه ریپوی GitHub بساز (مثلاً `shabpa-site`) و محتوای همین پوشه رو توش بذار (`_headers` باید ریشه‌ی ریپو باشه).
2. توی Cloudflare: Workers & Pages → Create → Pages → Connect to Git. Build command خالی، Output directory = `/`.
3. بعد از دیپلوی، Custom domain رو بزن: `shabpa.ir` و `www.shabpa.ir`.

## ۲. دامنه‌ی .ir
- دامنه‌ی .ir رو از پنل خودت توی نیک (nic.ir) باید به نیم‌سرورهای Cloudflare وصل کنی (nameserver ها رو Cloudflare نشون می‌ده).
- اگه nic.ir با نیم‌سرور Cloudflare مشکل داشت، می‌تونی فقط رکوردهای DNS رو (CNAME به آدرس pages.dev) از DNS خود nic.ir یا یه DNS دیگه بسازی؛ ولی هدرهای امنیتی و HTTPS خودکار Cloudflare رو از دست می‌دی.
- DNSSEC رو فعال کن (در Cloudflare و بعد DS record در nic.ir) اگه nic.ir ازش پشتیبانی می‌کرد.

## ۳. تنظیمات Cloudflare (SSL/TLS)
- Encryption mode: **Full (strict)**، Always Use HTTPS: روشن، Minimum TLS: 1.2، Automatic HTTPS Rewrites: روشن.
- HSTS رو فقط وقتی روشن کن که مطمئنی همه‌ی زیردامنه‌ها HTTPS دارن؛ `_headers` الان هم HSTS می‌فرسته (`preload` رو اگه نخواستی ثبت بشه حذف کن، برگشتش سخته).
- Bot Fight Mode و Security Level رو روی Medium بذار. اگه حمله‌ی DDoS دیدی «Under Attack» رو موقت روشن کن.

## ۴. حساب‌ها (مهم‌ترین بخش امنیت)
- **ورود دومرحله‌ای (2FA)** روی: GitHub، Cloudflare، حساب nic.ir و ایمیلی که به اونا وصله. بهتره با برنامه‌ی احراز هویت یا کلید سخت‌افزاری، نه پیامک.
- ایمیل ثبت دامنه‌ی nic.ir رو یه ایمیل مطمئن بذار (مالکیت دامنه با اون برمی‌گرده).
- قفل انتقال دامنه رو فعال نگه دار و تمدید دامنه رو یادآور بذار.
- روی ریپوی سایت: branch protection برای `main`، و Dependabot لازم نیست چون وابستگی نداریم.
- اگه ریپوی اپ (`shabpa`) رو هم داری: توکن‌ها رو منقضی‌شونده بساز و Actions secrets رو محدود نگه دار.

## ۵. چیزایی که توی خود سایت هست
- CSP سخت‌گیرانه (`default-src 'none'`، فقط اسکریپت و استایل همین دامنه، و ارتباط تنها با `api.github.com`).
- بدون اسکریپت یا استایل inline، بدون فونت یا کتابخونه‌ی خارجی (فونت وزیرمتن روی خود سایته؛ به گوگل درخواستی نمی‌ره).
- `X-Frame-Options`/`frame-ancestors none` (جلوگیری از clickjacking)، `nosniff`، `Referrer-Policy`، `Permissions-Policy`، `COOP/CORP`، HSTS.
- لینک دانلود فقط اگه با الگوی `github.com/MrPitPot/shabpa/releases/download/...` بخونه جایگزین می‌شه؛ SHA-256 از خود GitHub خونده می‌شه.
- `/.well-known/security.txt` برای گزارش آسیب‌پذیری (تاریخ انقضاش ۲۰۲۷-۱۰-۲۲ هست؛ سالی یه بار تمدید کن).

## ۶. بعد از دیپلوی تست کن
- <https://securityheaders.com> و <https://observatory.mozilla.org> (امتیاز باید A یا بالاتر باشه).
- <https://www.ssllabs.com/ssltest/>
- باز کردن سایت و چک «Console» بدون خطای CSP.

## ۷. نکته‌های اپ، نه سایت
- نصاب هنوز امضای دیجیتال نداره (SmartScreen هشدار می‌ده)؛ توی سوالات متداول توضیح داده شده. وقتی امضا بگیری، متن اون سوال رو عوض کن.
- winget هنوز منتشر نشده؛ بعد از پذیرفته‌شدن، دستور `winget install` رو به بخش دانلود اضافه کن.
- ایران: دسترسی به `github.com` و `api.github.com` ممکنه برای بعضی کاربرا قطع باشه. نصاب فقط ۵ مگابایته؛ می‌تونی یه آینه‌ی دانلود روی خود سایت (Pages تا ۲۵ مگ فایل می‌گیره) یا Cloudflare R2 بذاری. برای آینه حتماً SHA-256 رو هم کنارش منتشر کن.
