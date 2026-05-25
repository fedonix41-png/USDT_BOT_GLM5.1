"""Cross-dialect SQLAlchemy column types.

Provides types that work seamlessly across PostgreSQL (production)
and SQLite (tests), selecting the optimal native type for each dialect.
"""

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class JSONBCompat(TypeDecorator):
    """Type that renders as JSONB on PostgreSQL and JSON on other dialects.

    On PostgreSQL: uses native ``jsonb`` (binary JSON, indexable, faster queries).
    On SQLite and others: falls back to generic ``JSON`` (stored as TEXT,
    transparently serialised / deserialised).
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
