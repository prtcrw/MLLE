# MLLO Web

## Quick Start

0. Pre-requisite:

```
cd mllo_web/frontend/web
npm install
cd ../../..

virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. Build the UI:

```
cd mllo_web/frontend/web
npm install
npm run build
cd ../../..
```

2. Run api_app:

```
python -m mllo_web.app.api_app
```