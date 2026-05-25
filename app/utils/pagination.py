"""Pagination utilities."""

from app.config import settings


def calculate_pagination(total: int, offset: int, per_page: int | None = None) -> dict:
    """Calculate pagination metadata.

    Args:
        total: Total number of items.
        offset: Current offset.
        per_page: Items per page (default from settings).

    Returns:
        Dict with 'offset', 'limit', 'has_next', 'has_prev', 'total_pages', 'current_page'.
    """
    if per_page is None:
        per_page = settings.ORDERS_PER_PAGE

    current_page = (offset // per_page) + 1
    total_pages = max(1, -(-total // per_page))  # Ceiling division

    return {
        "offset": offset,
        "limit": per_page,
        "has_next": offset + per_page < total,
        "has_prev": offset > 0,
        "total_pages": total_pages,
        "current_page": current_page,
    }
