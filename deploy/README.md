# Public Beleg demo

The [public demo](https://mantakamahir.github.io/belegflow/) is a static site on
GitHub Pages. It shows three fictional cases and has no server runtime, database,
provider credentials, or visitor account. The full workbench runs separately; see
the [local setup](../README.md#quick-start).

## Build and preview

From the repository root, using only Python 3.11 or later:

```bash
python -m deploy.build_demo
python -m http.server 8128 --bind 127.0.0.1 --directory site/dist
```

Open `http://127.0.0.1:8128/`. `site/index.html` and `site/sample.html` are templates;
`site/dist/` is the generated site. The build reuses the local application's
fictional fixtures and decimal rounding. Browser code only changes the visible
sample or language and reveals lines cited as evidence.

GitHub Actions publishes only `site/dist/` on `main`. To deploy elsewhere, publish
that same directory with any static host. No Docker containers are needed.

## Custom hostname

`belegflow.gotiq.co` can be attached in the [GitHub Pages settings](https://github.com/MantakaMahir/belegflow/settings/pages).
Verify domain ownership with GitHub and register the Pages custom domain before
pointing only `belegflow.gotiq.co` at `mantakamahir.github.io` as a DNS-only CNAME.
Remove its obsolete Cloudflare Access gate and enable HTTPS in GitHub Pages.
Other DNS records, Access apps, and Cloudflare Tunnel routes are independent.
