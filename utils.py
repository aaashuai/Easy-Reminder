import io
import os
import re
import smtplib
from datetime import datetime, timedelta
from email.message import Message
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Union, Tuple

import qrcode
from dotenv import load_dotenv

from logger import logger
from ner.dtime.dtime import ZHDatetimeExtractor
from ner.number import ZHNumberExtractor
from typevar import JobScheduleType

load_dotenv()

ScheduleRe = re.compile(
    r"每((?P<daily>天|一天|1天)|(?P<days>(.*)天)|(?P<weekly>周[1-6一二三四五六日天]?)|(?P<monthly>月|个月)|(?P<yearly>年|1年|一年))(?P<date>.*)"
)


class TimeUtil:
    @staticmethod
    def datetime2timestamp(
        date_arg: Union[datetime, str], fmt: str = "%Y-%m-%d %H:%M:%S"
    ) -> int:
        if isinstance(date_arg, str):
            date_arg = datetime.strptime(date_arg, fmt)
        return int(date_arg.timestamp())

    @staticmethod
    def str2datetime(date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        return datetime.strptime(date_str, fmt)

    @staticmethod
    def timestamp2datetime(t_stamp: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return datetime.fromtimestamp(t_stamp).strftime(fmt)

    @staticmethod
    def seconds2date_str(seconds: int) -> str:
        """将秒转换为 天：时：分：秒"""

        if seconds is None:
            return ""
        d, h, m, s = (
            seconds // 86400,
            (seconds % 86400) // 3600,
            (seconds % 3600) // 60,
            seconds % 60,
        )

        txt = ""
        if d:
            txt += f"{d}天"
        if h:
            txt += f"{h}时"
        if m:
            txt += f"{m}分"
        if s:
            txt += f"{s}秒"
        return txt

    @staticmethod
    def now_datetime_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def now_datetime() -> datetime:
        return datetime.now()


class NerUtil:
    def __init__(self):
        self.date_extractor = ZHDatetimeExtractor(now_func=TimeUtil.now_datetime)
        self.num_extractor = ZHNumberExtractor()

    def extract_number(self, text: str) -> Optional[int]:
        res = self.num_extractor.parse(text)
        if not res:
            return
        logger.info(res)
        logger.info(res[0].num)
        return res[0].num

    def extract_time(
        self, text: str
    ) -> Optional[Tuple[int, Optional[JobScheduleType]]]:
        res = self.extract_schedule(text)
        if res:
            next_run_time, schedule_info = res
            return next_run_time, schedule_info
        return self.extract_once(text), None

    def extract_datetime(self, text: str) -> Optional[datetime]:
        res = self.date_extractor.parse(text)
        if not res:
            return
        logger.info(res)
        logger.info(res[0].values[-1].value)
        return res[0].values[-1].value

    def extract_once(self, text: str) -> Optional[int]:
        d_datetime = self.extract_datetime(text)
        assert d_datetime, "未获取到有效时间, 请重新输入"
        assert d_datetime > TimeUtil.now_datetime(), "设置时间必须大于现在"
        return int(d_datetime.timestamp())

    def _schedule_days_process(self, days: str):
        days = self.extract_number(days)
        next_run_time = int(
            (TimeUtil.now_datetime() + timedelta(days=days)).timestamp()
        )
        return next_run_time, days

    @staticmethod
    def _schedule_get_type(match_dict: dict) -> JobScheduleType:
        period = None
        for k, v in match_dict.items():
            if v:
                period = k
                break
        assert period, "为获取到有效周期, 请重新输入"
        return JobScheduleType.get_type(period)

    def _schedule_refresh_d_datetime(self, match_weekly: str) -> timedelta:
        now = TimeUtil.now_datetime()
        start_date = self.extract_datetime(match_weekly)
        # 处理今天周三, 询问周二, 日期获取的是昨天的情况
        days_7 = timedelta(days=7)
        if start_date.date() - now.date() == days_7:
            return timedelta(days=0)
        elif start_date.date() < now.date():
            start_date += days_7
        return timedelta(days=(start_date - now).days + 1)

    def extract_schedule(
        self, text: str
    ) -> Optional[Tuple[int, Union[JobScheduleType, int]]]:
        """返回下次时间和周期类型
        每周三下午六点 -> 下次运行时间戳, 一周的秒数
        """
        match_result = ScheduleRe.match(text)

        if not match_result:
            return

        match_dict = match_result.groupdict()
        given_date = match_dict.pop("date")
        # 指定具体日期周期的处理
        if match_dict["days"]:
            return self._schedule_days_process(match_dict["days"])

        d_datetime = self.extract_datetime(given_date)

        if not d_datetime:
            return

        schedule_type = self._schedule_get_type(match_dict)

        # 每周几的处理
        match_weekly = match_dict["weekly"]
        if match_weekly and len(match_weekly) != 1:
            d_datetime += self._schedule_refresh_d_datetime(match_weekly)

        if d_datetime <= TimeUtil.now_datetime():
            next_run_time = (
                TimeUtil.datetime2timestamp(d_datetime) + schedule_type.timestamp2now()
            )
        else:
            next_run_time = int(d_datetime.timestamp())

        return next_run_time, schedule_type.value


class QRCode:
    @staticmethod
    def qr_code_img(data: str, version=None) -> bytes:
        """
        create qr_code
        :param data: qrcode data
        :param version:1-40 or None
        :return:
        """
        qr = qrcode.QRCode(version)
        qr.add_data(data)
        if version:
            qr.make()
        else:
            qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr)
        return img_byte_arr.getvalue()


class Email:
    @staticmethod
    def construct_html(
        img_data: bytes, *, subject: str = "Wxbot Login", to: str = None
    ) -> MIMEMultipart:
        if to is None:
            to = os.getenv("MAIL_TO")
        me = os.getenv("MAIL_USER")
        assert all([to, me]), "mail info error"
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = me
        msg["To"] = to
        msg_str = """
        <p>qrcode:</p>
        <img src="cid:qrcode">
        """
        msg.attach(MIMEText(msg_str, "html", "utf8"))
        img = MIMEImage(img_data)
        img.add_header("Content-ID", "<qrcode>")
        msg.attach(img)
        return msg

    @staticmethod
    def send_email(msg: Message):
        mail_user, mail_pass = os.getenv("MAIL_USER"), os.getenv("MAIL_PASS")
        assert all([mail_user, mail_pass]), "mail info error"
        with smtplib.SMTP_SSL("smtp.163.com", 994) as s:
            s.login(os.getenv("MAIL_USER"), os.getenv("MAIL_PASS"))
            s.send_message(msg)
