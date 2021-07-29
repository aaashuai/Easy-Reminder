from peewee import SqliteDatabase

from dao import ScheduleJobDao, ScheduleRecordDao

old_db = SqliteDatabase("wxbot.db")


def refresh():
    data = list(old_db.execute_sql("select * from tableschedulejob"))
    alive_jobs = [d for d in data if d[-2] == 0]
    alive_job_msgs = set([d[-1] for d in alive_jobs])
    full_done_jobs = [d for d in data if d[-2] == 1 and d[-1] not in alive_job_msgs]
    only_done_jobs = set()
    done_jobs = []
    for d in full_done_jobs:
        if d[-1] in only_done_jobs:
            continue

        done_jobs.append(d)
        only_done_jobs.add(d[-1])

    cancel_jobs = [d for d in data if d[-2] == 2]
    full_jobs = sorted(
        [*alive_jobs, *done_jobs, *cancel_jobs], key=lambda x: (x[1], x[3])
    )

    row_map = {}
    for _, room, name, next_run_time, schedule_info, state, remind_msg in full_jobs:
        job_id = ScheduleJobDao.get_new_id(room)
        row = ScheduleJobDao.model.create(
            room=room,
            job_id=job_id,
            name=name,
            next_run_time=next_run_time,
            schedule_info=schedule_info,
            remind_msg=remind_msg,
            state=state,
        )
        row_map[remind_msg] = row.id

    for *_, remind_msg in sorted(full_done_jobs, key=lambda x: (x[1], x[3])):
        ScheduleRecordDao.create_record(row_map[remind_msg], remind_msg)


if __name__ == "__main__":
    refresh()
