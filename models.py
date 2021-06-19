from peewee import SqliteDatabase, Model, CharField, IntegerField, TextField

from typevar import JobState, JobType

db = SqliteDatabase('wxbot.db')


class TableScheduleJob(Model):
    id = IntegerField(index=True, primary_key=True)
    name = CharField(index=True, help_text="任务名称")
    next_run_time = IntegerField(help_text="下一次执行时间")
    type = IntegerField(choices=JobType, help_text="任务类型")
    state = IntegerField(default=JobState.ready, choices=JobState, help_text="任务执行状态")
    remind_msg = TextField(help_text="定时提醒内容")

    class Meta:
        database = db


def create_tables():
    with db:
        db.create_tables([TableScheduleJob])


create_tables()