from pydantic import BaseModel


class DashboardFilterQuery(BaseModel):
    year: int | None = None
    period: str | None = None
    """``AAAA-1`` o ``AAAA-2``."""
    moment: int | None = None
    """Momento de ESE (1, 2, 3; 4 solo en el histórico de 2024)."""
    simulation: str | None = None
    group: str | None = None
    test_type: str | None = None
    presented: bool | None = None
