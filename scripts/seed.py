"""Seed local Postgres with a dev user and a mock connector row."""
from __future__ import annotations

import os
import sys
import uuid

try:
    import psycopg
except ImportError:
    sys.stderr.write("psycopg not installed. Run: uv pip install psycopg[binary]\n")
    sys.exit(1)

DB_URL = os.environ.get("POSTGRES_URL", "postgresql://axis:axis@localhost:5432/axis")


def main() -> None:
    with psycopg.connect(DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        user_id = uuid.uuid4()
        cur.execute(
            """
            INSERT INTO users (id, email, name, plan)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            (user_id, "dev@axis.local", "Dev User", "pro"),
        )
        cur.execute(
            """
            INSERT INTO connectors (user_id, tool_name, status, permissions)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (user_id, tool_name) DO NOTHING
            """,
            (user_id, "slack", "connected", '{"read": true, "write": true}'),
        )
        print(f"seeded user {user_id}")


if __name__ == "__main__":
    main()
