"""Local dev launcher: `python run.py [port]` from the backend/ directory.

On Windows uvicorn 0.36+ forces a ProactorEventLoop, which psycopg cannot use
for async connections. Pass an explicit loop factory so the async pool works.
"""

import sys

import uvicorn

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    kwargs = {"loop": "asyncio:SelectorEventLoop"} if sys.platform == "win32" else {}
    uvicorn.run("main:app", host="0.0.0.0", port=port, **kwargs)
