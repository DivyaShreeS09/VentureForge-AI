"""Cross-backend column types: real JSONB on PostgreSQL, plain JSON elsewhere (SQLite in tests),
so the same models work against a fast in-memory test database and real Postgres in production.
"""

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

JSONVariant = JSON().with_variant(JSONB(), "postgresql")
UUIDType = Uuid(as_uuid=True)
