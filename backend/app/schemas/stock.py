from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StockQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    company: str | None
    price: float
    change: float | None
    change_percent: float | None
    previous_close: float | None
    timestamp: datetime | None
    data_source: str
    market_data_status: Literal["realtime", "delayed", "end_of_day", "unknown"]
