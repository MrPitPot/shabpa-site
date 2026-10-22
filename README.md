# shabpa-site

Website for [Shabpa](https://github.com/MrPitPot/shabpa), served at <https://shabpa.ir>.

Static HTML/CSS/JS with no build step and no dependencies. The site is the `public/` folder; security headers (CSP, HSTS, ...) live in `public/_headers`.

```bash
npx wrangler pages deploy public --project-name shabpa
```

See [DEPLOY.md](DEPLOY.md) for hosting and account-security notes (in Persian).

The Vazirmatn font (SIL OFL) is bundled in `public/assets/fonts`. App screenshots are generated from Shabpa's `--screenshots` mode with demo data.
