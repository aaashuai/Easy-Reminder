from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Union, Text

from pydantic import BaseModel


class Entity(BaseModel):
    entity: Text
    start_pos: int
    end_pos: int


class Number(Entity):
    num: Union[int, float]


class DatetimeTypeEnum(str, Enum):
    date = "date"
    datetime = "datetime"
    time = "time"
    duration = "duration"

    def __repr__(self):
        return f"DatetimeTypeEnum.{self.value}"


class Datetime(Entity):
    class Value(BaseModel):
        value: Optional[datetime]
        delta: Optional[timedelta]

    type: DatetimeTypeEnum
    is_range: bool
    is_multivalue: bool
    datetime_level: List[int]
    values: List[Value]
