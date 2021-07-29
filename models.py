import time

from peewee import SqliteDatabase, Model, CharField, IntegerField, TextField

from typevar import JobState

db = SqliteDatabase("wxbotv2.db")


class TableScheduleJob(Model):
    id = IntegerField(index=True, primary_key=True, help_text="真实ID")
    job_id = IntegerField(index=True, help_text="任务ID")
    room = TextField(index=True, help_text="群聊房间")
    name = CharField(index=True, help_text="任务名称")
    start_time = IntegerField(default=lambda: int(time.time()), help_text="开始时间")
    next_run_time = IntegerField(help_text="下一次执行时间")
    schedule_info = CharField(null=True, help_text="周期类型或天数")
    state = IntegerField(default=JobState.ready, choices=JobState, help_text="任务执行状态")
    remind_msg = TextField(help_text="定时提醒内容")

    class Meta:
        database = db


class TableScheduleRecord(Model):
    id = IntegerField(index=True, primary_key=True)
    job_real_id = IntegerField(index=True, help_text="任务真实ID")
    remind_msg = TextField(help_text="本次提醒内容")
    create_time = IntegerField(default=lambda: int(time.time()), help_text="执行时间")

    class Meta:
        database = db


def create_tables():
    with db:
        db.create_tables([TableScheduleJob, TableScheduleRecord])


create_tables()
