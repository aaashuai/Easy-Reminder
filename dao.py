import uuid
from typing import Tuple, Union, List

from models import TableScheduleJob
from typevar import JobState, JobScheduleType


class ScheduleJobDao:
    model = TableScheduleJob

    @classmethod
    def get_all_jobs(
        cls, room_id: str = None, state: JobState = JobState.ready
    ) -> Tuple[int, List[TableScheduleJob]]:
        query_filter = []
        if state is not None:
            query_filter.append(cls.model.state == state)
        if room_id:
            query_filter.append(cls.model.room_id == room_id)
        query = cls.model.select()
        if query_filter:
            query = query.where(*query_filter)
        return query.count(), query.order_by(-cls.model.id)

    @classmethod
    def create_job(
        cls,
        room_id: str,
        next_run_time: int,
        remind_msg: str,
        schedule_info: Union[str, int] = None,
        name: str = None,
    ) -> TableScheduleJob:
        if name is None:
            name = str(uuid.uuid4())
        return cls.model.create(
            room_id=room_id,
            name=name,
            next_run_time=next_run_time,
            schedule_info=schedule_info,
            remind_msg=remind_msg,
        )

    @classmethod
    def update_job(cls, job_id: int, next_run_time: int) -> int:
        return (
            cls.model.update(next_run_time=next_run_time)
            .where(cls.model.id == job_id)
            .execute()
        )

    @classmethod
    def job_done(cls, job_id) -> int:
        return (
            cls.model.update(state=JobState.done)
            .where(cls.model.id == job_id)
            .execute()
        )

    @classmethod
    def cancel_job(cls, job_id: int) -> int:
        return (
            cls.model.update(state=JobState.cancel)
            .where(cls.model.id == job_id)
            .execute()
        )


if __name__ == "__main__":
    # r = ScheduleJobDao.create_job(room_id=1, next_run_time=1, job_type=0, remind_msg='test')
    c, j = ScheduleJobDao.get_all_jobs(state=JobState.done)
    print(c)
    print(list(j))
