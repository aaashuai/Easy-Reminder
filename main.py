import asyncio
import functools
import inspect
import os
import time
from typing import Optional

from wechaty import Wechaty, Room, Message, WechatyOptions, Contact
from wechaty_puppet import RoomQueryFilter, ScanStatus

from constants import EN2ZH_MAP
from dao import ScheduleJobDao, ScheduleRecordDao
from logger import logger
from typevar import JobScheduleType
from utils import TimeUtil, NerUtil, QRCode, Email


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
        self._commands = {}

        for _, method in inspect.getmembers(
            ReminderBot, predicate=inspect.iscoroutinefunction
        ):
            cmd = getattr(method, "__command__", None)
            if cmd:
                self._commands[cmd] = method

        self.ner = NerUtil()

    async def on_login(self, contact: Contact):
        await asyncio.sleep(3)
        logger.info("login success")
        asyncio.create_task(self._run_schedule_task())

    async def _run_schedule_task(self):
        while True:
            _, all_jobs = ScheduleJobDao.get_all_jobs()
            cur_time = int(time.time())
            for job in all_jobs:
                # 允许1秒以内的误差
                if abs(job.next_run_time - cur_time) <= 1:
                    try:
                        await self._remind_something(
                            room=job.room,
                            job_id=job.job_id,
                            remind_msg=job.remind_msg,
                            schedule_info=job.schedule_info,
                            current_run_time=job.next_run_time,
                        )
                    except Exception as e:
                        logger.warning(f"错误: {e}")
                    continue
                # 已经过了执行时间的任务提醒未完成, 并更新
                elif job.next_run_time < cur_time:
                    try:
                        await self._remind_failed_msg(
                            room=job.room,
                            job_id=job.job_id,
                            remind_msg=job.remind_msg,
                            schedule_info=job.schedule_info,
                            current_run_time=job.next_run_time,
                        )
                    except Exception as e:
                        logger.warning(f"错误: {e}")
                    continue

            await asyncio.sleep(1)

    async def _remind_failed_msg(
        self,
        room: str,
        job_id: int,
        current_run_time: int,
        remind_msg: str,
        schedule_info: Optional[str],
    ):
        logger.info(f"task failed, room:{room},job_id:{job_id},remind_msg:{remind_msg}")
        reminder_room = await self.Room.find(RoomQueryFilter(topic=room))
        assert reminder_room, f"未找到群聊: {room}"
        await reminder_room.ready()
        send_msg = (
            "任务超时, 应执行时间为:\n"
            f"{TimeUtil.timestamp2datetime(current_run_time)}\n"
            f"内容:\n"
            f"{remind_msg}"
        )
        ScheduleRecordDao.create_record(job_id, remind_msg)
        if not schedule_info:
            ScheduleJobDao.job_done(job_id, room=room)
            await reminder_room.say(f"{send_msg}")
            logger.info(f"task done, room:{room},job_id:{job_id},remind_msg:{send_msg}")
            return
        while True:
            next_run_time = self._renew_job(
                room=room,
                job_id=job_id,
                remind_msg=remind_msg,
                schedule_info=schedule_info,
                current_run_time=current_run_time,
            )
            if next_run_time > int(time.time()):
                break
            current_run_time = next_run_time

        await reminder_room.say(
            f"{send_msg}\n"
            f"下一次执行时间: \n"
            f"{TimeUtil.timestamp2datetime(next_run_time)}"
        )
        logger.info(f"task done, room:{room},job_id:{job_id},remind_msg:{send_msg}")

    async def _remind_something(
        self,
        room: str,
        job_id: int,
        current_run_time: int,
        remind_msg: str,
        schedule_info: Optional[str],
    ):
        logger.info(
            f"task execute, room:{room},job_id:{job_id},remind_msg:{remind_msg}"
        )
        reminder_room = await self.Room.find(RoomQueryFilter(topic=room))
        assert reminder_room, f"未找到群聊: {room}"
        await reminder_room.ready()
        send_msg = (
            f"{TimeUtil.timestamp2datetime(current_run_time)}\n"
            f"内容:\n"
            f"{remind_msg}"
        )
        ScheduleRecordDao.create_record(job_id, remind_msg)
        if not schedule_info:
            ScheduleJobDao.job_done(job_id, room=room)
            await reminder_room.say(f"{send_msg}")
            logger.info(f"task done, room:{room},job_id:{job_id},remind_msg:{send_msg}")
            return

        next_run_time = self._renew_job(
            room=room,
            job_id=job_id,
            remind_msg=remind_msg,
            schedule_info=schedule_info,
            current_run_time=current_run_time,
        )
        await reminder_room.say(
            f"{send_msg}\n"
            f"下一次执行时间: \n"
            f"{TimeUtil.timestamp2datetime(next_run_time)}"
        )
        logger.info(f"task done, room:{room},job_id:{job_id},remind_msg:{send_msg}")

    @staticmethod
    def _renew_job(
        room: str,
        job_id: int,
        remind_msg: str,
        schedule_info: str,
        current_run_time: int,
    ) -> int:
        """周期性任务重新创建"""
        if schedule_info not in JobScheduleType.all_values():
            time_diff = int(schedule_info) * 24 * 60 * 60
        else:
            time_diff = JobScheduleType.get_type(schedule_info).timestamp2now()
        next_run_time = current_run_time + time_diff
        ScheduleJobDao.update_job(
            job_id=job_id,
            room=room,
            next_run_time=next_run_time,
            remind_msg=remind_msg,
        )
        return next_run_time

    async def on_message(self, msg: Message):
        text = msg.text()
        room = msg.room()
        # 仅回复群聊及其他人消息
        if room is None or msg.is_self():
            return

        try:
            cmd, *args = text.translate(EN2ZH_MAP).split(",")
            if cmd in self._commands:
                await room.ready()
                await self._commands[cmd](self, *args, room=room)
            else:
                await room.ready()
                await room.say(f"无此命令: {cmd}\n当前支持命令:\n{', '.join(self._commands)}")
        except Exception as e:
            await room.ready()
            await room.say(f"处理消息失败:\n{text}\n\n{e}")

    async def on_scan(
        self, qr_code: str, status: ScanStatus, data: Optional[str] = None
    ):
        try:
            Email.send_email(Email.construct_html(QRCode.qr_code_img(qr_code)))
            logger.info("send qrcode to email success")
        except Exception as e:
            logger.error("send qrcode to email failed: ", e)

    async def on_logout(self, contact: Contact):
        # todo use docker to run wechaty
        def restart_pi_wechaty():
            os.system(
                "rm /home/ubuntu/projects/wechaty/python-wechaty-l.memory-card.json"
            )
            os.system("supervisorctl restart wechaty")

        try:
            restart_pi_wechaty()
            logger.info("restart wechaty success")
        except Exception as e:
            logger.error("restart wechaty failed, ", e)

    @command("all tasks")
    async def all_tasks(self, *args, room: Room, **kwargs):
        """获取当前任务列表
        > all tasks
        """
        job_count, all_jobs = ScheduleJobDao.get_all_jobs(room.payload.topic)
        if not job_count:
            return await room.say("当前无生效任务\n请通过 [ remind,日期,提醒内容 ] 进行创建")
        txt = f"当前共有{job_count}条任务: \n"
        for i, job in enumerate(all_jobs, start=1):
            txt += (
                f"{'-' * 25}\n"
                f"ID:{job.job_id}\n"
                f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                f"内容:{job.remind_msg}\n"
            )
        await room.say(txt)

    @command
    async def remind(self, *args, room: Room, **kwargs):
        """创建一条提醒记录
        > remind,提醒时间,提醒内容
        例:
        > remind,明天上午11点,吃东西
        """
        given_time, remind_msg, *remind_left = args
        remind_msg = ", ".join([remind_msg, *remind_left])
        next_run_time, schedule_info = self.ner.extract_time(given_time)
        job = ScheduleJobDao.create_job(
            room=room.payload.topic,
            next_run_time=next_run_time,
            remind_msg=remind_msg,
            schedule_info=schedule_info,
        )
        assert job, "任务失败, 请重试"
        await room.say(
            f"任务已创建\n"
            f"ID:{job.job_id}\n"
            f"下一次执行时间:\n{TimeUtil.timestamp2datetime(next_run_time)}\n"
            f"内容:{remind_msg}\n"
        )

    @command
    async def cancel(self, *args, room: Room, **kwargs):
        """取消一条任务/多条任务
        > cancel,id[,id2...]
        例:
        > cancel,12
        > cancel,12,13,14
        """
        job_id, *other_job_ids = args
        assert int(job_id), "任务ID不合法"
        if other_job_ids:
            assert [int(j_id) for j_id in other_job_ids], "任务ID不合法"

        nrows = ScheduleJobDao.cancel_jobs(
            job_id, *other_job_ids, room=room.payload.topic
        )
        assert nrows == len([job_id, *other_job_ids]), "任务失败, 请重试"

        txt = f"ID:{', '.join([job_id, *other_job_ids])}, 任务已取消\n\n"

        job_count, all_jobs = ScheduleJobDao.get_all_jobs(room.payload.topic)
        if not job_count:
            txt += "当前已无生效任务\n请通过 [ remind,日期,提醒内容 ] 进行创建"
            return await room.say(txt)

        txt += f"当前还有{job_count}条任务:\n"
        for i, job in enumerate(all_jobs, start=1):
            txt += (
                f"{'-' * 25}\n"
                f"{i}. ID:{job.job_id}\n"
                f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                f"内容:{job.remind_msg}\n"
            )
        await room.say(txt)

    @command("help")
    async def show_help(self, *args, room: Room, **kwargs):
        """显示某命令使用方法
        > help,remind
        """
        cmd, *_ = args
        assert (
            cmd in self._commands
        ), f"无此命令: {cmd}\n当前支持命令:\n{', '.join(self._commands)}"
        docs = self._commands[cmd].__doc__

        await room.say("\n".join([l.strip() for l in docs.split("\n")]))

    @command("room info")
    async def show_room_info(self, *args, room: Room, **kwargs):
        """获取当前群聊信息
        > room info
        """
        await room.say(f"Topic: {room.payload.topic}\n" f"Id: {room.room_id}")

    @command
    async def update(self, *args, room: Room, **kwargs):
        """更新某个任务
        > update,id,时间,内容 (m:id, o:时间, o:内容)
        > update,12,明天上午9点,吃东西
        > update,12,,吃东西
        > update,12,后天上午9点,
        """
        job_id, n_time, *n_msg = args
        assert job_id and int(job_id), "请填写正确的ID"
        assert n_time or n_msg, "时间和内容必须修改一项"
        _update = {}
        if n_time:
            next_run_time, schedule_info = self.ner.extract_time(n_time)
            _update.update(next_run_time=next_run_time, schedule_info=schedule_info)

        if n_msg:
            remind_msg = ", ".join(n_msg)
            _update.update(remind_msg=remind_msg)

        nrow = ScheduleJobDao.update_job(
            job_id=int(job_id), room=room.payload.topic, **_update
        )
        assert nrow, "没有这个ID, 任务失败, 请重试"
        job = ScheduleJobDao.get_job(job_id=int(job_id), room=room.payload.topic)
        await room.say(
            f"任务已更新\n"
            f"ID:{job.job_id}\n"
            f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
            f"内容:{job.remind_msg}\n"
        )


async def main():
    bot = ReminderBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
