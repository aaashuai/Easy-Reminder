from enum import IntEnum, unique, Enum
from dateutil import relativedelta
from datetime import date


@unique
class JobState(IntEnum):
    ready = 0
    done = 1
    cancel = 2


@unique
class JobScheduleType(Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"
    # days = 4  # 指定天数的不用type标记, 数据库中直接存对应天数

    @staticmethod
    def all_values() -> list:
        return [j.value for j in JobScheduleType]

    @classmethod
    def get_type(cls, j_type: str) -> "JobScheduleType":
        return {t.name: t for t in cls}.get(j_type)

    def timestamp2now(self) -> int:
        if self == JobScheduleType.daily:
            diff_delta = relativedelta.relativedelta(days=1)
        elif self == JobScheduleType.weekly:
            diff_delta = relativedelta.relativedelta(weeks=1)
        elif self == JobScheduleType.monthly:
            diff_delta = relativedelta.relativedelta(months=1)
        else:
            diff_delta = relativedelta.relativedelta(years=1)

        return ((date.today() + diff_delta) - date.today()).days * 24 * 60 * 60


if __name__ == '__main__':
    print(JobScheduleType.all_values())