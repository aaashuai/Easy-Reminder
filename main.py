import asyncio
import functools
import inspect
import os
import time
from typing import Optional

from dotenv import load_dotenv
from icecream import ic
from wechaty import Wechaty, Room, Message, WechatyOptions
from wechaty_puppet import FileBox
from pyunit_time import Time

from dao import ScheduleJobDao

load_dotenv()

ROOM_ID = os.environ.get("ROOM_ID")  # 群聊 ID
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

        for _, method in inspect.getmembers(ReminderBot, predicate=inspect.iscoroutinefunction):
            cmd = getattr(method, "__command__", None)
            if cmd:
                self._commands[cmd] = method

    async def _run_schedule_task(self):
        while True:
            all_jobs = ScheduleJobDao.get_all_jobs()
            min_sleep = -1
            cur_time = int(time.time())
            for job in all_jobs:
                # 允许3秒以内的误差
                if abs(job.next_run_time - cur_time) <= 3:
                    asyncio.create_task(self._remind_something(job.id, job.name, job.remind_msg))
                    continue
                next_job_interval = job.next_run_time - cur_time
                min_sleep = (
                    min(min_sleep, next_job_interval)
                    if min_sleep > 0 and next_job_interval > 0
                    else next_job_interval
                )
            sleep_time = min_sleep if min_sleep > 0 else 1
            await asyncio.sleep(sleep_time)

    async def _remind_something(self, job_id: int, name: str, remind_msg: str):
        ic("task execute")
        reminder_room = await self.Room.find(ROOM_ID)
        await reminder_room.say(f"当前任务: {name}\n提醒内容: {remind_msg}")
        ScheduleJobDao.job_done(job_id)
        ic("task done")

    async def on_message(self, msg: Message):
        text = msg.text()
        room = msg.room()
        from_contact = msg.talker()
        # 仅回复群聊问题
        if room is None or from_contact.get_id() == SELF_ID:
            return

        try:
            cmd, *args = text.split(",")
            if cmd in self._commands:
                await room.ready()
                await self._commands[cmd](self, *args, room=room)
            else:
                await room.ready()
                await room.say(f"无此命令: {cmd}\n当前支持命令: {', '.join(self._commands)}")
        except Exception as e:
            await room.ready()
            await room.say(f"处理消息失败: {text}, {e}")

    @command
    async def ding(self, *args, room: Room, **kwargs):
        await room.say("dong")
        file_box = FileBox.from_url(
            "https://ss3.bdstatic.com/70cFv8Sh_Q1YnxGkpoWK1HF6hhy/it/"
            "u=1116676390,2305043183&fm=26&gp=0.jpg",
            name="ding-dong.jpg",
        )
        await room.say(file_box)

    @command("all tasks")
    async def all_tasks(self, *args, room: Room, **kwargs):
        await room.say("This is show_my_tasks")

    @command
    async def task(self, *args, room: Room, **kwargs):
        await room.say(f"This is task register, args: {args}, kwargs: {kwargs}")

    @command
    async def cancel(self, *args, room: Room, **kwargs):
        await room.say(f"This is cancel, args: {args}, kwargs: {kwargs}")

    @command("help")
    async def show_help(self, *args, room: Room, **kwargs):
        await room.say(f"This is help, args: {args}, kwargs: {kwargs}")


async def main():
    bot = ReminderBot()
    await bot.start()


if __name__ == '__main__':
    # asyncio.run(main())
    print(Time("2021-06-19 00:00:00").parse("每天10点"))
