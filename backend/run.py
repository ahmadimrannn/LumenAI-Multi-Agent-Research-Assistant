"""Local dev launcher: `python run.py` from the backend/ directory.

uvicorn creates its event loop before importing the app, so the Windows event
loop policy has to be set here rather than in main.py -- otherwise psycopg's
async pool is handed a ProactorEventLoop it cannot use.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
