import asyncio
import functools
import inspect
import os
import time
from datetime import datetime
from typing import Optional, Union

from dotenv import load_dotenv
from wechaty import Wechaty, Room, Message, WechatyOptions
from wechaty_puppet import FileBox

from dao import ScheduleJobDao
from logger import logger
from models import TableScheduleJob
from typevar import JobScheduleType
from utils import TimeUtil, NerUtil

load_dotenv()

SELF_ID = os.environ.get("SELF_ID")  # 机器人 ID


def command(arg):
    """装饰器, 将命令注册到wxbot"""

    cmd = arg if isinstance(arg, str) else arg.__name__

    def _decorator(fn):
        assert inspect.iscoroutinefunction(fn), "only async method allowed"
        assert "room" in inspect.signature(fn).parameters, "room needed"
        fn.__command__ = cmd

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)

        return wrapper

    # 方法名即命令
    if inspect.isfunction(arg):
        return _decorator(arg)

    # 参数即命令
    return _decorator


class ReminderBot(Wechaty):
    def __init__(self, options: Optional[WechatyOptions] = None):
        super().__init__(options)
        asyncio.create_task(self._run_schedule_task())
        self._commands = {}

        for _, method in inspect.getmembers(
            ReminderBot, predicate=inspect.iscoroutinefunction
        ):
            cmd = getattr(method, "__command__", None)
            if cmd:
                self._commands[cmd] = method

    async def _run_schedule_task(self):
        while True:
            _, all_jobs = ScheduleJobDao.get_all_jobs()
            # min_sleep = -1
            cur_time = int(time.time())
            for job in all_jobs:
                # 允许1秒以内的误差
                if abs(job.next_run_time - cur_time) <= 1:
                    await self._remind_something(
                        room_id=job.room_id,
                        job_id=job.id,
                        remind_msg=job.remind_msg,
                        job_name=job.name,
                        schedule_info=job.schedule_info,
                    )
                    continue
                # next_job_interval = job.next_run_time - cur_time
                # min_sleep = (
                #     min(min_sleep, next_job_interval)
                #     if min_sleep > 0 and next_job_interval > 0
                #     else next_job_interval
                # )
            # sleep_time = min_sleep if min_sleep > 0 else 1
            # await asyncio.sleep(sleep_time)
            await asyncio.sleep(1)

    async def _remind_something(
        self,
        room_id: str,
        job_id: int,
        remind_msg: str,
        job_name: Optional[str],
        schedule_info: Optional[str],
    ):
        logger.info(
            f"task execute, room_id:{room_id},job_id:{job_id},remind_msg:{remind_msg}"
        )
        reminder_room = await self.Room.find(room_id)
        ScheduleJobDao.job_done(job_id)
        send_msg = (
            f"{TimeUtil.now_datetime_str()}\n"
            f"内容:\n"
            f"{remind_msg}"
        )
        if not schedule_info:
            await reminder_room.say(f"{send_msg}")
            logger.info(
                f"task done, room_id:{room_id},job_id:{job_id},remind_msg:{send_msg}"
            )
            return

        job = self._renew_job(
            room_id=room_id,
            job_name=job_name,
            remind_msg=remind_msg,
            schedule_info=schedule_info,
        )
        await reminder_room.say(
            f"{send_msg}\n"
            f"下一次执行时间: \n"
            f"{TimeUtil.timestamp2datetime(job.next_run_time)}"
        )
        logger.info(
            f"task done, room_id:{room_id},job_id:{job_id},remind_msg:{send_msg}"
        )

    @staticmethod
    def _renew_job(
        room_id: str,
        job_name: str,
        remind_msg: str,
        schedule_info: str,
    ) -> TableScheduleJob:
        """周期性任务重新创建"""
        now = datetime.now()
        if schedule_info not in JobScheduleType.all_values():
            time_diff = int(schedule_info) * 24 * 60 * 60
        else:
            time_diff = JobScheduleType.get_type(schedule_info).timestamp2now()
        next_run_time = int(now.timestamp()) + time_diff
        return ScheduleJobDao.create_job(
            room_id=room_id,
            name=job_name,
            next_run_time=next_run_time,
            remind_msg=remind_msg,
            schedule_info=schedule_info,
        )

    async def on_message(self, msg: Message):
        text = msg.text()
        room = msg.room()
        from_contact = msg.talker()
        # 仅回复群聊问题
        if room is None or from_contact.get_id() == SELF_ID:
            return
        table = {
            ord(f): ord(t)
            for f, t in zip("，。！？【】（）％＃＠＆１２３４５６７８９０", ",.!?[]()%#@&1234567890")
        }

        try:
            cmd, *args = text.translate(table).split(",")
            if cmd in self._commands:
                await room.ready()
                await self._commands[cmd](self, *args, room=room)
            else:
                await room.ready()
                await room.say(
                    f"无此命令: {cmd}\n"
                    "当前支持命令:\n"
                    f"{', '.join(self._commands)}"
                )
        except Exception as e:
            await room.ready()
            await room.say(f"处理消息失败:\n{text}\n\n{e}")

    @command("all tasks")
    async def all_tasks(self, *args, room: Room, **kwargs):
        job_count, all_jobs = ScheduleJobDao.get_all_jobs(room.room_id)
        if not job_count:
            return await room.say("当前无生效任务\n请通过 [ remind,日期,提醒内容 ] 进行创建")
        txt = f"当前共有{job_count}条任务: \n"
        for i, job in enumerate(all_jobs, start=1):
            txt += (
                f"{'-' * 25}\n"
                f"ID:{job.id}\n"
                f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                f"内容:{job.remind_msg}\n"
            )
        await room.say(txt)

    @command
    async def remind(self, *args, room: Room, **kwargs):
        given_time, remind_msg, *_ = args
        next_run_time, schedule_info = NerUtil.extract_time(given_time)
        job = ScheduleJobDao.create_job(
            room_id=room.room_id,
            next_run_time=next_run_time,
            remind_msg=remind_msg,
            schedule_info=schedule_info,
        )
        assert job, "任务失败, 请重试"
        await room.say(
            f"任务已创建\n"
            f"ID:{job.id}\n"
            f"下一次执行时间:\n{TimeUtil.timestamp2datetime(next_run_time)}\n"
            f"内容:{remind_msg}\n"
        )

    @command
    async def cancel(self, *args, room: Room, **kwargs):
        job_id, *_ = args
        assert int(job_id), "任务ID不合法"
        is_success = ScheduleJobDao.cancel_job(job_id)
        assert is_success > 0, "任务失败, 请重试"
        txt = f"ID:{job_id}, 任务已取消\n\n"

        job_count, all_jobs = ScheduleJobDao.get_all_jobs(room.room_id)
        if not job_count:
            txt += "当前已无生效任务\n请通过 [ remind,日期,提醒内容 ] 进行创建"
            return await room.say(txt)

        txt += f"当前还有{job_count}条任务:\n"
        for i, job in enumerate(all_jobs, start=1):
            txt += (
                f"{'-' * 25}\n"
                f"{i}. ID:{job.id}\n"
                f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                f"内容:{job.remind_msg}\n"
            )
        await room.say(txt)

    @command("help")
    async def show_help(self, *args, room: Room, **kwargs):
        await room.say(f"This is help, args: {args}, kwargs: {kwargs}")


async def main():
    bot = ReminderBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
