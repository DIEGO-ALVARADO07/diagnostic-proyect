from pydantic import BaseModel


class DashboardFilterQuery(BaseModel):
    year: int | None = None
    period: str | None = None
    """``AAAA-1`` o ``AAAA-2``."""
    moment: int | None = None
    """Momento de ESE (1, 2, 3)."""
    simulation: str | None = None
    group: str | None = None
    semester: str | None = None
    test_type: str | None = None
    presented: bool | None = None
