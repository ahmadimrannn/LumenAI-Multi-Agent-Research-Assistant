import os
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool, AsyncConnectionPool
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve PostgreSQL database connection URI from environment
POSTGRES_DB_URI = os.getenv("POSTGRES_DB_URI")

# Initialize PostgreSQL Connection Pool (sync — used by the LangGraph checkpointer,
# which runs the graph in a worker thread)
pool = ConnectionPool(
  conninfo=POSTGRES_DB_URI,
  max_size=10,
  max_idle=300,
  kwargs={
      "autocommit": True,
      "prepare_threshold": 0,
      "row_factory": dict_row,
  },
  check=ConnectionPool.check_connection
)

# Async pool for the FastAPI endpoints; opened/closed in main.py's lifespan.
# A sync pool cannot be used with `async with pool.connection()`.
async_pool = AsyncConnectionPool(
  conninfo=POSTGRES_DB_URI,
  max_size=10,
  max_idle=300,
  kwargs={
      "autocommit": True,
      "prepare_threshold": 0,
      "row_factory": dict_row,
  },
  check=AsyncConnectionPool.check_connection,
  open=False,
)

# Initialize LangGraph Postgres Checkpointer
checkpointer = PostgresSaver(pool, serde=JsonPlusSerializer())

# Automatically create necessary checkpoint tables in PostgreSQL if they do not exist
checkpointer.setup()

