from datetime import datetime, timedelta
from typing import Optional, Union, Tuple

from logger import logger
from ner.dtime.dtime import date_extractor
import re

from ner.number import number_ext
from typevar import JobScheduleType

ScheduleRe = re.compile(r"每((?P<daily>天|一天|1天)|(?P<days>(.*)天)|(?P<weekly>周)|(?P<monthly>月|个月)|(?P<yearly>年|1年|一年))(?P<date>.*)")


class NerUtil:
    @classmethod
    def extract_number(cls, text: str) -> Optional[int]:
        res = number_ext.parse(text)
        if not res:
            return
        logger.info(res)
        logger.info(res[0].num)
        return res[0].num

    @classmethod
    def extract_time(cls, text: str) -> Optional[Tuple[int, Optional[JobScheduleType]]]:
        res = cls.extract_schedule(text)
        if res:
            next_run_time, schedule_info = res
            return next_run_time, schedule_info
        return cls.extract_once(text), None

    @staticmethod
    def extract_datetime(text: str) -> Optional[datetime]:
        res = date_extractor.parse(text)
        if not res:
            return
        logger.info(res)
        logger.info(res[0].values[-1].value)
        return res[0].values[-1].value

    @classmethod
    def extract_once(cls, text: str) -> Optional[int]:
        d_datetime = cls.extract_datetime(text)
        assert d_datetime, "未获取到有效时间, 请重新输入"
        now = datetime.now()
        assert d_datetime > now, "设置时间必须大于现在"
        return int(d_datetime.timestamp())

    @classmethod
    def extract_schedule(cls, text: str) -> Optional[Tuple[int, Union[JobScheduleType, int]]]:
        """返回下次时间和周期类型
        每周三 -> 下次运行时间戳, 一周的秒数
        """
        match_result = ScheduleRe.match(text)

        if not match_result:
            return

        match_dict = match_result.groupdict()
        given_date = match_dict.pop("date")
        # 指定具体日期周期的处理
        if match_dict["days"]:
            days = NerUtil.extract_number(match_dict["days"])
            next_run_time = int((datetime.now() + timedelta(days=days)).timestamp())
            return next_run_time, days

        d_datetime = cls.extract_datetime(given_date)

        if not d_datetime:
            return

        period = None
        for k, v in match_dict.items():
            if v:
                period = k
                break
        assert period, "为获取到有效周期, 请重新输入"
        schedule_type = JobScheduleType.get_type(period)

        now = datetime.now()
        if d_datetime <= now:
            next_run_time = TimeUtil.datetime2timestamp(d_datetime) + schedule_type.timestamp2now()
        else:
            next_run_time = int(d_datetime.timestamp())

        return next_run_time, schedule_type.value


class TimeUtil:
    @staticmethod
    def datetime2timestamp(date_arg: Union[datetime, str], fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
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
        d, h, m, s = seconds // 86400, (seconds % 86400) // 3600, (seconds % 3600) // 60, seconds % 60

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


if __name__ == '__main__':
    assert TimeUtil.seconds2date_str(15) == '15秒', TimeUtil.seconds2date_str(15)
    assert TimeUtil.seconds2date_str(61) == '1分1秒', TimeUtil.seconds2date_str(61)
    assert TimeUtil.seconds2date_str(3661) == '1时1分1秒', TimeUtil.seconds2date_str(3661)
    assert TimeUtil.seconds2date_str(90061) == '1天1时1分1秒', TimeUtil.seconds2date_str(90061)

    # while True:
    #     print('-'*30)
    #     try:
    #         txt = input("date: ")
    #         job_type, next_run_time, period_type = NerUtil.extract_time(txt)
    #         print(job_type.name)
    #         print(TimeUtil.timestamp2datetime(next_run_time))
    #         print(period_type)
    #     except Exception as e:
    #         print(str(e))
    while True:
        print('-'*30)
        try:
            txt = input("number: ")
            print(NerUtil.extract_number(txt))
        except Exception as e:
            print(str(e))
