from typing import Literal, Optional, Any
from pydantic import BaseModel


class Result(BaseModel):
    result: Literal["Ok", "Failed"]
    message: Optional[str] = None
    data: Optional[Any] = None
