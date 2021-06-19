from enum import IntEnum, unique


@unique
class JobState(IntEnum):
    ready = 0
    done = 1
    cancel = 2


@unique
class JobType(IntEnum):
    once = 0
    schedule = 1
