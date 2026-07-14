import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

DATABASE_PATH = Path(__file__).resolve().parent.parent / "database" / "lumen_checkpoints.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

checkpointer = SqliteSaver(conn=connection)
checkpointer.setup()