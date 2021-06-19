import time

from models import TableScheduleJob
from typevar import JobState, JobType


class ScheduleJobDao:
    model = TableScheduleJob

    @classmethod
    def get_all_jobs(cls):
        return cls.model.select().where(cls.model.state == JobState.ready).order_by(-cls.model.id)

    @classmethod
    def create_job(cls, name: str, next_run_time: int, job_type: JobType, remind_msg: str):
        cls.model.create(
            name=name,
            next_run_time=next_run_time,
            type=job_type,
            remind_msg=remind_msg,
        )

    @classmethod
    def update_job(cls, job_id: int, next_run_time: int):
        cls.model.update(next_run_time=next_run_time).where(cls.model.id == job_id).execute()

    @classmethod
    def job_done(cls, job_id):
        cls.model.update(state=JobState.done).where(cls.model.id == job_id).execute()

    @classmethod
    def cancel_job(cls, job_id: int):
        cls.model.update(state=JobState.cancel).where(cls.model.id == job_id).execute()


if __name__ == '__main__':
    ScheduleJobDao.create_job("test", int(time.time()+10), JobType.once, remind_msg="this is tester")