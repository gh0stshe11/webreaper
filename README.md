# webReaper v0.6

Adds **banner polish (colors + bold + dim blades)** and a **color-coded Markdown report** (badges + legend).

## Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run
```bash
webreaper reap https://example.com -o out/
```

### Filters (examples)
```bash
webreaper reap https://example.com -o out/ \
  --exclude-ext png,jpg,jpeg,gif,css,js,svg,ico,woff,woff2 \
  --exclude-path logout,signout \
  --max-params 8
```
