import uuid
from typing import Tuple, Union, List, Optional

from models import TableScheduleRecord, TableScheduleJob
from typevar import JobState


class ScheduleRecordDao:
    model = TableScheduleRecord

    @classmethod
    def create_record(cls, job_real_id: int, remind_msg: str) -> TableScheduleRecord:
        return cls.model.create(job_real_id=job_real_id, remind_msg=remind_msg)


class ScheduleJobDao:
    model = TableScheduleJob

    @classmethod
    def get_all_jobs(
        cls, room: str = None, state: JobState = JobState.ready
    ) -> Tuple[int, List[TableScheduleJob]]:
        query_filter = []
        if state is not None:
            query_filter.append(cls.model.state == state)
        if room:
            query_filter.append(cls.model.room == room)
        query = cls.model.select()
        if query_filter:
            query = query.where(*query_filter)
        return query.count(), query.order_by(cls.model.next_run_time)

    @classmethod
    def get_new_id(cls, room: str) -> int:
        row = (
            cls.model.select()
            .where(cls.model.room == room)
            .order_by(-cls.model.job_id)
            .first()
        )
        return row.job_id + 1 if row else 1

    @classmethod
    def create_job(
        cls,
        room: str,
        next_run_time: int,
        remind_msg: str,
        schedule_info: Union[str, int] = None,
        name: str = None,
    ) -> TableScheduleJob:
        if name is None:
            name = str(uuid.uuid4())
        job_id = cls.get_new_id(room)
        return cls.model.create(
            room=room,
            job_id=job_id,
            name=name,
            next_run_time=next_run_time,
            schedule_info=schedule_info,
            remind_msg=remind_msg,
        )

    @classmethod
    def update_job(
        cls,
        job_id: int,
        room: str,
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
        return (
            cls.model.update(**_update)
            .where(cls.model.job_id == job_id, cls.model.room == room)
            .execute()
        )

    @classmethod
    def job_done(cls, job_id: int, room: str) -> int:
        return (
            cls.model.update(state=JobState.done)
            .where(cls.model.job_id == job_id, cls.model.room == room)
            .execute()
        )

    @classmethod
    def cancel_jobs(cls, *job_ids: int, room: str) -> int:
        return (
            cls.model.update(state=JobState.cancel)
            .where(cls.model.job_id.in_(job_ids), cls.model.room == room)
            .execute()
        )

    @classmethod
    def get_job(
        cls, job_id: int, room: str, job_state: JobState = JobState.ready
    ) -> Optional[TableScheduleJob]:
        return cls.model.get_or_none(
            cls.model.job_id == job_id,
            cls.model.room == room,
            cls.model.state == job_state,
        )


if __name__ == "__main__":
    c, j = ScheduleJobDao.get_all_jobs(state=JobState.done)
    print(c)
    print(list(j))
