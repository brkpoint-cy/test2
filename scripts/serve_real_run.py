# -*- coding: utf-8 -*-
"""Serve the web UI against the real observed-data run for report screenshots."""
from pathlib import Path

import uvicorn

from changchun_air.web_api import app, store

REAL_RUN = Path(__file__).resolve().parent.parent / "artifacts" / "web-runs" / "94469c656403"

store.publish(REAL_RUN)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)
