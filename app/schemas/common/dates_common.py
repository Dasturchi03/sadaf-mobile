import re
from datetime import date
from typing import Annotated, Union
from fastapi import Depends, Query
from pydantic import BaseModel


MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


class MonthRange(BaseModel):
    """Month range calculated from YYYY-MM: [start, end)"""
    start: date
    end: date

    @property
    def year(self) -> int:
        return self.start.year

    @property
    def month(self) -> int:
        return self.start.month


def parse_yyyy_mm_to_range(v: Union[str, date, MonthRange]) -> MonthRange:
    """
    Normolizes input value to MonthRange:
    - 'YYYY-MM' satr → MonthRange(start=YYYY-MM-01, end=next-month-01)
    """
    if isinstance(v, MonthRange):
        return v

    if isinstance(v, date):
        y, m = v.year, v.month
    elif isinstance(v, str):
        mobj = MONTH_RE.fullmatch(v)
        if not mobj:
            raise ValueError("for_month must match YYYY-MM (e.g. 2025-08)")
        y, m = int(mobj.group(1)), int(mobj.group(2))
    else:
        raise TypeError("Expected 'YYYY-MM' string or date")

    start = date(y, m, 1)
    next_y = y + (m // 12)
    next_m = (m % 12) + 1
    end = date(next_y, next_m, 1)
    return MonthRange(start=start, end=end)


def get_current_month_str() -> str:
    today = date.today()
    return f"{today:%Y-%m}"


def for_month_dep(
    raw: Annotated[
        str,
        Query(
            description="YYYY-MM (e.g. 2025-08)",
            examples=["2025-08"],
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
            default_factory=get_current_month_str,
        ),
    ]
) -> MonthRange:
    return parse_yyyy_mm_to_range(raw)


ForMonth = Annotated[MonthRange, Depends(for_month_dep)]
