from pydantic import BaseModel


class DashboardFilterQuery(BaseModel):
    year: int | None = None
    simulation: str | None = None
    group: str | None = None
    semester: str | None = None
    test_type: str | None = None
    presented: bool | None = None
