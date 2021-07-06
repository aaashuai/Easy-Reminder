import uuid
from typing import Tuple, Union, List, Optional

from models import TableScheduleJob
from typevar import JobState


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
        return query.count(), query.order_by(cls.model.next_run_time)

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
    def update_job(
        cls,
        job_id: int,
        next_run_time: int = None,
        remind_msg: str = None,
        schedule_info: Union[str, int] = None,
    ) -> int:
        _update = {}
        if next_run_time:
            _update["next_run_time"] = next_run_time
        if schedule_info:
            _update["schedule_info"] = schedule_info
        if remind_msg:
            _update["remind_msg"] = remind_msg

        assert _update, "你必须更新点什么"
        return cls.model.update(**_update).where(cls.model.id == job_id).execute()

    @classmethod
    def job_done(cls, job_id: int, room_id: str) -> int:
        return (
            cls.model.update(state=JobState.done)
            .where(cls.model.id == job_id, cls.model.room_id == room_id)
            .execute()
        )

    @classmethod
    def cancel_jobs(cls, *job_ids: int, room_id: str) -> int:
        return (
            cls.model.update(state=JobState.cancel)
            .where(cls.model.id.in_(job_ids), cls.model.room_id == room_id)
            .execute()
        )

    @classmethod
    def get_job(
        cls, job_id: int, room_id: str, job_state: JobState = JobState.ready
    ) -> Optional[TableScheduleJob]:
        return cls.model.get_or_none(
            cls.model.id == job_id,
            cls.model.room_id == room_id,
            cls.model.state == job_state,
        )


if __name__ == "__main__":
    c, j = ScheduleJobDao.get_all_jobs(state=JobState.done)
    print(c)
    print(list(j))
