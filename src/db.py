"""Shared PostgreSQL connection helper, configured via .env."""

from pathlib import Path

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, Engine

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_database_url() -> str:
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine() -> Engine:
    return create_engine(get_database_url())
