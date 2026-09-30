"""Shared PostgreSQL connection helper.

Locally, config comes from .env (POSTGRES_* vars, Docker Postgres).
On Streamlit Community Cloud there's no .env or Docker, so the same vars
(or a single DATABASE_URL) are read from st.secrets instead, set via the
app's Settings -> Secrets panel.
"""

from pathlib import Path

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, Engine

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_config() -> dict:
    """Merge st.secrets (if running under Streamlit, e.g. on Community Cloud)
    over os.environ (local .env / Docker), so either source can supply config."""
    config = dict(os.environ)
    try:
        import streamlit as st

        config.update(st.secrets)
    except Exception:
        pass
    return config


def get_database_url() -> str:
    config = _get_config()

    database_url = config.get("DATABASE_URL") or config.get("POSTGRES_URL")
    if database_url:
        return database_url

    user = config["POSTGRES_USER"]
    password = config["POSTGRES_PASSWORD"]
    host = config.get("POSTGRES_HOST", "localhost")
    port = config.get("POSTGRES_PORT", "5432")
    db = config["POSTGRES_DB"]
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine() -> Engine:
    return create_engine(get_database_url())
