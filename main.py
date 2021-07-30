import asyncio
import inspect
import os
import re
import time
from collections import Iterable
from typing import Optional, Union

from wechaty import Wechaty, Room, Message, WechatyOptions, Contact, MiniProgram, UrlLink
from wechaty_puppet import RoomQueryFilter, ScanStatus, FileBox

from constants import EN2ZH_MAP
from crawler.weather import weather_selenium
from dao import ScheduleJobDao, ScheduleRecordDao
from logger import logger
from typevar import JobScheduleType
from utils import TimeUtil, NerUtil, QRCode, Email, r_command, r_template


class RenderTemplate:
    """模板渲染
    你好, [weather:北京]
    """
    def __init__(self):
        self._templates = r_template.get_members(RenderTemplate)
        self.re = re.compile(r"[\[](.*?)[\]]", re.S)

    def _parse(self, msg: str):
        """-> cmd, args"""
        ret = []
        for item in self.re.finditer(msg):  # 早上好, 今天的天气 [weather:北京:朝阳]
            match_msg = item.group()  # [weather:北京:朝阳]
            pre, _next = msg.split(match_msg)
            template, *args = match_msg[1:-1].split(":")
            if template in self._templates:
                res = self._templates[template](self, *args)
                if isinstance(res, str):
                    msg = "".join([pre, res, _next])
                    continue
                else:
                    msg = "".join([pre, _next])
                if isinstance(res, Iterable):
                    ret.extend(res)
                else:
                    ret.append(res)
        return msg, ret

    def render(self, msg: str) -> list:
        msg, others = self._parse(msg)
        return [msg, *others]

    def show_help(self, template: str):
        """显示模板消息帮助
        """
        assert (
            template in self._templates
        ), f"无此模板: {template}\n当前支持模板:\n{', '.join(self._templates)}"
        return self._templates[template].__doc__

    @r_template
    def weather(self, *args) -> FileBox:
        """[模板]获取某城市天气
        > [weather:朝阳:北京]
        > [weather:北京]
        """
        location, *adm = args
        adm = adm[0] if adm else None
        summary = weather_selenium.craw_weather(location, adm)
        with open("summary.png", "wb") as fp:
            fp.write(summary)
        s_box = FileBox.from_file("summary.png", "summary.png")
        return s_box


class ReminderBot(Wechaty):
    def __init__(self, options: Optional[WechatyOptions] = None):
        super().__init__(options)
        self._commands = r_command.get_members(ReminderBot)
        self._render_template = RenderTemplate()
        self.ner = NerUtil()
        self.login = False

    def render_msg(self, msg: str) -> list:
        return self._render_template.render(msg)

    async def render(self, room: Room, send_msg: Union[str, Contact, FileBox, MiniProgram, UrlLink]):
        await room.ready()
        msgs = self.render_msg(send_msg)
        for msg in msgs:
            await room.say(msg)

    @staticmethod
    async def say(room: Room, send_msg: Union[str, Contact, FileBox, MiniProgram, UrlLink]):
        await room.ready()
        await room.say(send_msg)

    async def on_login(self, contact: Contact):
        await asyncio.sleep(3)
        logger.info("login success")
        self.login = True
        asyncio.create_task(self._run_schedule_task())

    async def on_message(self, msg: Message):
        text = msg.text()
        room = msg.room()
        # 仅回复群聊及其他人消息
        if room is None or msg.is_self():
            return

        try:
            cmd, *args = text.translate(EN2ZH_MAP).split(",")
            if cmd in self._commands:
                func = self._commands[cmd]
                if inspect.iscoroutinefunction(func):
                    await func(self, *args, room=room)
                else:
                    func(self, *args, room=room)
            else:
                await self.say(
                    room, f"无此命令: {cmd}\n当前支持命令:\n{', '.join(self._commands)}"
                )
        except Exception as e:
            await self.say(room, f"处理消息失败:\n{text}\n\n{e}")

    async def on_scan(
        self, qr_code: str, status: ScanStatus, data: Optional[str] = None
    ):
        try:
            Email.send_email(Email.construct_html(QRCode.qr_code_img(qr_code)))
            logger.info("send qrcode to email success")
        except Exception as e:
            logger.error("send qrcode to email failed: ", e)

    async def on_logout(self, contact: Contact):
        self.login = False

        # todo use docker to run wechaty
        def restart_pi_wechaty():
            os.system("bash /home/ubuntu/projects/wechaty/shutdown.sh")
            os.system("supervisorctl restart wechaty")

        try:
            restart_pi_wechaty()
            logger.info("restart wechaty success")
        except Exception as e:
            logger.error("restart wechaty failed, ", e)

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
                            send_msg=(
                                f"{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                                f"内容:\n"
                                f"{job.remind_msg}"
                            ),
                        )
                    except Exception as e:
                        logger.exception(f"错误: {e}")
                    continue
                # 已经过了执行时间的任务提醒未完成, 并更新
                elif job.next_run_time < cur_time:
                    try:
                        await self._remind_something(
                            room=job.room,
                            job_id=job.job_id,
                            remind_msg=job.remind_msg,
                            schedule_info=job.schedule_info,
                            current_run_time=job.next_run_time,
                            send_msg=(
                                "任务超时, 应执行时间为:\n"
                                f"{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                                f"内容:\n"
                                f"{job.remind_msg}"
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"错误: {e}")
                    continue

            await asyncio.sleep(1)

    async def _remind_once(
        self, job_id: int, room: str, reminder_room: Room, send_msg: str
    ):
        ScheduleJobDao.job_done(job_id, room=room)
        await self.render(reminder_room, f"{send_msg}")
        logger.info(f"task done, room:{room},job_id:{job_id},remind_msg:{send_msg}")
        return

    @staticmethod
    def _renew_job(
        room: str,
        job_id: int,
        remind_msg: str,
        schedule_info: str,
        current_run_time: int,
    ) -> int:
        """周期性任务重新创建"""

        now_time = int(time.time())
        while True:
            if schedule_info not in JobScheduleType.all_values():
                time_diff = int(schedule_info) * 24 * 60 * 60
            else:
                time_diff = JobScheduleType.get_type(schedule_info).timestamp2now()
            next_run_time = current_run_time + time_diff
            if next_run_time > now_time:
                break

        ScheduleJobDao.update_job(
            job_id=job_id,
            room=room,
            next_run_time=next_run_time,
            remind_msg=remind_msg,
        )
        return next_run_time

    async def _remind_schedule(
        self,
        room: str,
        job_id: int,
        remind_msg: str,
        schedule_info: str,
        current_run_time: int,
        reminder_room: Room,
        send_msg: str,
    ):
        next_run_time = self._renew_job(
            room=room,
            job_id=job_id,
            remind_msg=remind_msg,
            schedule_info=schedule_info,
            current_run_time=current_run_time,
        )
        await self.render(
            reminder_room,
            f"{send_msg}\n"
            f"下一次执行时间: \n"
            f"{TimeUtil.timestamp2datetime(next_run_time)}",
        )
        logger.info(f"task done, room:{room},job_id:{job_id},remind_msg:{send_msg}")

    async def _remind_something(
        self,
        room: str,
        job_id: int,
        current_run_time: int,
        remind_msg: str,
        send_msg: str,
        schedule_info: Optional[str],
    ):
        logger.info(
            f"task execute, room:{room},job_id:{job_id},remind_msg:{remind_msg}"
        )
        reminder_room = await self.Room.find(RoomQueryFilter(topic=room))
        assert reminder_room, f"未找到群聊: {room}"
        await reminder_room.ready()
        ScheduleRecordDao.create_record(job_id, remind_msg)
        if not schedule_info:
            return await self._remind_once(job_id, room, reminder_room, send_msg)
        return await self._remind_schedule(
            room,
            job_id,
            remind_msg,
            schedule_info,
            current_run_time,
            reminder_room,
            send_msg,
        )

    @r_command("all tasks")
    async def all_tasks(self, *args, room: Room, **kwargs):
        """获取当前任务列表
        > all tasks
        """
        job_count, all_jobs = ScheduleJobDao.get_all_jobs(room.payload.topic)
        if not job_count:
            return await self.say(room, "当前无生效任务\n请通过 [ remind,日期,提醒内容 ] 进行创建")

        txt = f"当前共有{job_count}条任务: \n"
        for i, job in enumerate(all_jobs, start=1):
            txt += (
                f"{'-' * 25}\n"
                f"ID:{job.job_id}\n"
                f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                f"内容:{job.remind_msg}\n"
            )
        await self.say(room, txt)

    @r_command
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
        await self.say(
            room,
            f"任务已创建\n"
            f"ID:{job.job_id}\n"
            f"下一次执行时间:\n{TimeUtil.timestamp2datetime(next_run_time)}\n"
            f"内容:{remind_msg}\n",
        )

    @r_command
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
            return await self.say(room, txt)

        txt += f"当前还有{job_count}条任务:\n"
        for i, job in enumerate(all_jobs, start=1):
            txt += (
                f"{'-' * 25}\n"
                f"{i}. ID:{job.job_id}\n"
                f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
                f"内容:{job.remind_msg}\n"
            )
        await self.say(room, txt)

    @r_command("help")
    async def show_help(self, *args, room: Room, **kwargs):
        """显示某命令使用方法
        > help,remind
        """
        cmd, *other_args = args
        assert (
            cmd in {*self._commands, "template"}  # todo 有没有更优雅的形式
        ), f"无此命令: {cmd}\n当前支持命令:\n{', '.join([*self._commands, 'template'])}"
        if cmd == "template":
            docs = self._render_template.show_help(other_args[0])
        else:
            docs = self._commands[cmd].__doc__

        await self.say(room, "\n".join([l.strip() for l in docs.split("\n")]))

    @r_command("room info")
    async def show_room_info(self, *args, room: Room, **kwargs):
        """获取当前群聊信息
        > room info
        """
        await self.say(room, f"Topic: {room.payload.topic}\n" f"Id: {room.room_id}")

    @r_command
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
        await self.say(
            room,
            f"任务已更新\n"
            f"ID:{job.job_id}\n"
            f"下一次执行时间:\n{TimeUtil.timestamp2datetime(job.next_run_time)}\n"
            f"内容:{job.remind_msg}\n",
        )


async def main():
    bot = ReminderBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
