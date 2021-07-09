import regex as re
from datetime import datetime, time
from typing import Optional, Dict, Union, Tuple, List, Callable
from typing import Any, Text

from dateutil.relativedelta import relativedelta

from ner import BaseExtractor
from ner.models import Datetime
from ner.number import number_ext
from ner.dtime.date_pattern import YEAR_OPTIONAL_DATE, YEAR

__all__ = ("DateObject", "Duration", "ZHDatetimeExtractor", "date_extractor")


# Duration除外的日期表达
class DateObject:
    def __init__(
        self,
        now,
        entity,
        parse_code,
        datetime_level,
        is_discrete,
        is_range,
        datetime_type,
        base_time=None,
        period=(0, 0, 0, 0),
        duration=(0, 0, 0, 0),
        is_week=None,
        is_specific_time=None,
        **data,
    ):
        """
        :param now:
        :param entity: 提取出的实体，比如"周三"
        :param parse_code:
        :param datetime_level: [0,0,0,0,0,0]六位占位符列表，分别对应[年，月，日，时，分，秒]，0为该位无值，1为有值
        :param is_discrete: [x,x]两位列表，x取值为None,0,1; 其中第一位代表Date，第二位代表Time，非None代表为对应类型，比如[1, 1]代表Datetime类型，且Date和Time处is_discrete都为True
        :param is_range: 与is_discrete类似
        :param datetime_type:
        :param base_time:
        :param period: [year, month, day, second]
        :param duration: [year, month, day, second]
        :param is_week:
        :param is_specific_time:
        :param data:
        """
        self.now = now
        self.entity = entity
        self.parse_code = parse_code
        self.datetime_level = datetime_level
        self.is_discrete = is_discrete
        self.is_range = is_range
        self.datetime_type = datetime_type
        self.base_time = base_time
        self.period = list(period)
        self.duration = list(duration)
        self.is_week = is_week
        self.is_specific_time = is_specific_time
        self.value = None
        self.nearest = None
        self.data = data
        self.parse_dict = {
            0: self.parse_input_0,
            2: self.parse_input_1,
            4: self.adjust_base_to_previous,
            5: self.adjust_base_to_previous,
            6: self.parse_input_2,
            8: self.parse_input_2,
            10: self.parse_input_3,
            11: self.parse_input_3,
            12: self.parse_input_3,
            13: self.parse_input_3,
            14: self.parse_input_3,
            15: self.parse_input_3,
            16: self.parse_input_3,
            17: self.parse_input_3,
            18: self.parse_input_3,
            19: self.parse_input_3,
            20: self.parse_input_3,
            21: self.parse_input_3,
            22: self.parse_input_3,
            23: self.parse_input_3,
            24: self.parse_input_4,
            25: self.parse_input_4,
            26: self.parse_input_4,
            27: self.parse_input_4,
            28: self.parse_input_4,
            29: self.parse_input_4,
            31: self.parse_input_5,
            32: self.parse_input_5,
            33: self.parse_input_5,
            34: self.parse_input_4,
            35: self.parse_input_4,
            36: self.parse_input_4,
            45: self.parse_input_2,
        }
        self.relative_date_dict = {
            "本": 0,
            "这": 0,
            "今": 0,
            "来": 1,
            "去": -1,
            "昨": -1,
            "明": 1,
            "上": -1,
            "下": 1,
            "这1": 0,
            "上1": -1,
            "下1": 1,
            "这个": 0,
            "上个": -1,
            "下个": 1,
            "前个": -1,
            "后个": 1,
            "这1个": 0,
            "上1个": -1,
            "下1个": 1,
            "前": -2,
            "后": 2,
            "大前": -3,
            "大后": 3,
        }
        self.holiday_dict = {
            "元旦": (datetime(2018, 1, 1), datetime(2019, 1, 1), datetime(2020, 1, 1)),
            "除夕": (datetime(2018, 2, 15), datetime(2019, 2, 4), datetime(2020, 1, 24)),
            "年30": (datetime(2018, 2, 15), datetime(2019, 2, 4), datetime(2020, 1, 24)),
            "春节": (datetime(2018, 2, 16), datetime(2019, 2, 5), datetime(2020, 1, 25)),
            "清明": (datetime(2018, 4, 5), datetime(2019, 4, 5), datetime(2020, 4, 5)),
            "劳动": (datetime(2018, 5, 1), datetime(2019, 5, 1), datetime(2020, 5, 1)),
            "端午": (datetime(2018, 6, 18), datetime(2019, 6, 7), datetime(2020, 6, 25)),
            "中秋": (datetime(2018, 9, 24), datetime(2019, 9, 13), datetime(2020, 10, 1)),
            "国庆": (datetime(2018, 10, 1), datetime(2019, 10, 1), datetime(2020, 10, 1)),
            "圣诞": (
                datetime(2018, 12, 25),
                datetime(2019, 12, 25),
                datetime(2020, 12, 25),
            ),
        }
        self.timerange_dict = {
            "清晨": (4, 4),
            "黎明": (4, 4),
            "早上": (6, 6),
            "早晨": (6, 6),
            "上午": (6, 6),
            "晌午": (8, 4),
            "中午": (11, 2),
            "午间": (11, 2),
            "午后": (12, 4),
            "下午": (12, 4),
            "黄昏": (16, 4),
            "傍晚": (16, 4),
            "晚上": (18, 8),
            "夜晚": (18, 4),
            "晚间": (18, 4),
            "深夜": (20, 4),
            "凌晨": (0, 6),
        }
        self.time_dict = {"正午": 12, "半夜": 0, "午夜": 0}
        self.datetimerange_dict = {
            "今早": (6, 6, 0),
            "今晚": (18, 4, 0),
            "今夜": (18, 4, 0),
            "昨晚": (18, 4, -1),
            "昨夜": (18, 4, -1),
            "明早": (6, 6, 1),
            "明晚": (18, 4, 1),
        }

    def __repr__(self):
        return "{}({}, {}, {}, {}, {}, {})".format(
            self.datetime_type,
            self.datetime_level,
            self.is_discrete,
            self.is_range,
            self.entity,
            self.value,
            self.nearest,
        )

    def __add__(self, other):
        assert type(other) == DateObject
        # 如果两个相加对象同为Daterange, Timerange, Datetimerange，则返回None
        for i in range(2):
            if self.is_range[i] == 1 and other.is_range[i] == 1:
                return None
        fst_lowest, snd_highest = 5, 0
        for i in range(5, -1, -1):
            if self.datetime_level[i]:
                fst_lowest = i
                break
        for i in range(6):
            if other.datetime_level[i]:
                snd_highest = i
                break
        # timelevel正好相差1位
        if (
            (snd_highest - fst_lowest == 1)
            or (
                (self.is_week == 1)
                and (other.parse_code == 27)
                and (other.is_week == 2)
            )
            or (self.is_specific_time and (snd_highest == 3))
        ):
            if self.is_week is None:
                if other.is_week:
                    return False
            else:
                if self.is_week == 1:
                    if other.is_week is None:
                        return False
            # TODO 2021年节假日还需修改这里
            if other.parse_code == 30:
                if (
                    (self.base_time.year != 2018)
                    and (self.base_time.year != 2019)
                    and (self.base_time.year != 2020)
                ) or (not (self.is_range[0])):
                    return False
            if self.is_specific_time and not (snd_highest == 3):
                return False
            sum_entity = self.entity + other.entity
            sum_datetime_level = [
                a ^ b for (a, b) in zip(self.datetime_level, other.datetime_level)
            ]
            if other.parse_code == 27:
                sum_datetime_level = [0] * 6
            if self.is_specific_time:
                sum_datetime_level[3] = 1
            sum_is_discrete = self.add_discrete_range_helper(
                zip(self.is_discrete, other.is_discrete)
            )
            sum_is_range = self.add_discrete_range_helper(
                zip(self.is_range, other.is_range)
            )
            sum_period = [0, 0, 0, 0]
            if sum_is_discrete[0]:
                sum_period[0:3] = self.period[0:3]
            if sum_is_discrete[1]:
                if self.is_discrete[1]:
                    sum_period[3] = self.period[3]
                else:
                    sum_period[3] = other.period[3]
            sum_duration = [0, 0, 0, 0]
            if sum_is_range[0]:
                sum_duration[0:3] = other.duration[0:3]
            if sum_is_range[1]:
                if self.is_range[1]:
                    sum_duration[3] = other.duration[3]
                else:
                    sum_duration[3] = other.duration[3]
            sum_datetime_type = self.calculate_datetime_type(sum_is_range)
            if other.parse_code == 30:
                sum_base_time = self.holiday_dict[other.entity][
                    self.base_time.year - 2018
                ]
            else:
                sum_base_time = self.add_base_time_helper(self.base_time, other)
            if not sum_base_time:
                return "Illegal"
            sum_date_object = DateObject(
                self.now,
                sum_entity,
                -1,
                sum_datetime_level,
                sum_is_discrete,
                sum_is_range,
                sum_datetime_type,
                sum_base_time,
                sum_period,
                sum_duration,
            )
            if other.is_specific_time:
                sum_date_object.is_specific_time = 1
            if self.parse_code == 30:
                temp1 = DateObject(
                    self.now,
                    sum_entity,
                    -1,
                    sum_datetime_level,
                    sum_is_discrete,
                    sum_is_range,
                    sum_datetime_type,
                    self.add_base_time_helper(self.value[0], other),
                    sum_period,
                    sum_duration,
                )
                temp2 = DateObject(
                    self.now,
                    sum_entity,
                    -1,
                    sum_datetime_level,
                    sum_is_discrete,
                    sum_is_range,
                    sum_datetime_type,
                    self.add_base_time_helper(
                        self.value[int(len(self.value) / 2)], other
                    ),
                    sum_period,
                    sum_duration,
                )
                temp1.parse_input()
                temp2.parse_input()
                sum_date_object.parse_code = 30
                if type(temp1.value) == list:
                    sum_date_object.value = temp1.value + temp2.value
                else:
                    sum_date_object.value = [temp1.value, temp2.value]
                sum_date_object.calculate_nearest()
            else:
                sum_date_object.parse_input()
            return sum_date_object
        else:
            return False

    @staticmethod
    def add_discrete_range_helper(zip_list):
        rtn = []
        for (a, b) in zip_list:
            if (a is None) and (b is None):
                rtn.append(None)
            elif a is None:
                rtn.append(b)
            elif b is None:
                rtn.append(a)
            else:
                rtn.append(a & b)
        return rtn

    def add_base_time_helper(self, base_time, other):
        sum_base_time = base_time
        if type(sum_base_time) == dict:
            sum_base_time = sum_base_time["start"]
        if other.is_week == 2:
            if (other.base_time >= base_time) and (
                other.base_time < (base_time + relativedelta(weeks=1))
            ):
                sum_base_time = other.base_time
            elif (other.base_time - relativedelta(weeks=1) >= base_time) and (
                other.base_time - relativedelta(weeks=1)
                < (base_time + relativedelta(weeks=1))
            ):
                sum_base_time = other.base_time - relativedelta(weeks=1)
            elif (other.base_time + relativedelta(weeks=1) >= base_time) and (
                other.base_time + relativedelta(weeks=1)
                < (base_time + relativedelta(weeks=1))
            ):
                sum_base_time = other.base_time + relativedelta(weeks=1)
            else:
                sum_base_time = other.base_time + relativedelta(weeks=2)
        elif self.is_specific_time:
            found = False
            if self.is_range[1]:
                if "上午" in self.entity:
                    check_start = time(0, 0, 1)
                    check_end = time(12)
                elif "下午" in self.entity:
                    check_start = time(12, 0, 1)
                    check_end = time(0)
                else:
                    if type(self.value) == list:
                        check_range = self.value[0]
                    else:
                        check_range = self.value
                    check_start = check_range["start"].time()
                    check_end = check_range["end"].time()
                if other.is_discrete[1]:
                    for value in other.value:
                        if "晚上" in self.entity:
                            if (value.time() >= check_start) and (
                                value.time() <= time(23, 59, 59)
                            ):
                                sum_base_time = sum_base_time.replace(
                                    hour=value.hour, minute=value.minute
                                )
                                found = True
                                break
                            elif (value.time() >= time(0)) and (
                                value.time() <= check_end
                            ):
                                sum_base_time = sum_base_time.replace(
                                    day=sum_base_time.day + 1,
                                    hour=value.hour,
                                    minute=value.minute,
                                )
                                found = True
                                break
                        else:
                            if (value.time() == time(0)) and (check_end == time(0)):
                                sum_base_time = sum_base_time.replace(
                                    day=sum_base_time.day + 1,
                                    hour=value.hour,
                                    minute=value.minute,
                                )
                                found = True
                                break
                            elif (value.time() >= check_start) and (
                                (value.time() <= check_end) or (check_end == time(0))
                            ):
                                sum_base_time = sum_base_time.replace(
                                    hour=value.hour, minute=value.minute
                                )
                                found = True
                                break
                else:
                    if "晚上" in self.entity:
                        if (other.value.time() >= check_start) and (
                            other.value.time() <= time(23, 59, 59)
                        ):
                            sum_base_time = sum_base_time.replace(
                                hour=other.value.hour, minute=other.value.minute
                            )
                            found = True
                        elif (other.value.time() >= time(0)) and (
                            other.value.time() <= check_end
                        ):
                            sum_base_time = sum_base_time.replace(
                                day=sum_base_time.day + 1,
                                hour=other.value.hour,
                                minute=other.value.minute,
                            )
                            found = True
                    else:
                        if (other.value.time() == time(0)) and (check_end == time(0)):
                            sum_base_time = sum_base_time.replace(
                                day=sum_base_time.day + 1,
                                hour=other.value.hour,
                                minute=other.value.minute,
                            )
                            found = True
                        elif (other.value.time() >= check_start) and (
                            (other.value.time() <= check_end) or (check_end == time(0))
                        ):
                            sum_base_time = sum_base_time.replace(
                                hour=other.value.hour, minute=other.value.minute
                            )
                            found = True
                if not found:
                    return False
            else:
                if type(self.value) == list:
                    check_time = self.value[0].time()
                else:
                    check_time = self.value.time()
                for value in other.value:
                    if value.time() == check_time:
                        found = True
                        break
                if not found:
                    return False
        else:
            if other.datetime_level[1]:
                sum_base_time = sum_base_time.replace(month=other.base_time.month)
            if other.datetime_level[2]:
                sum_base_time = sum_base_time.replace(day=other.base_time.day)
            if other.datetime_level[3]:
                sum_base_time = sum_base_time.replace(hour=other.base_time.hour)
            if other.datetime_level[4]:
                sum_base_time = sum_base_time.replace(minute=other.base_time.minute)
            if other.datetime_level[5]:
                sum_base_time = sum_base_time.replace(second=other.base_time.second)
        return sum_base_time

    @staticmethod
    def calculate_datetime_type(is_range):
        if is_range[1] is None:
            if is_range[0]:
                return "DateRange"
            else:
                return "Date"
        else:
            if is_range[0] is None:
                if is_range[1]:
                    return "TimeRange"
                else:
                    return "Time"
            else:
                if is_range[1]:
                    return "DatetimeRange"
                else:
                    return "Datetime"

    # 调整离散日期的base_time为现在的上一个日期
    def adjust_base_to_previous(self):
        if self.base_time > self.now:
            self.base_time -= relativedelta(
                years=self.period[0],
                months=self.period[1],
                days=self.period[2],
                seconds=self.period[3],
            )

    # 类似"(年.)月.日"的处理
    def parse_input_0(self):
        if self.data["year"]:
            self.base_time = datetime(
                int(self.data["year"]), int(self.data["month"]), int(self.data["day"])
            )
        else:
            self.datetime_level[0] = 0
            self.is_discrete[0] = 1
            self.period[0] = 1
            self.base_time = datetime(
                self.now.year, int(self.data["month"]), int(self.data["day"])
            )
            self.adjust_base_to_previous()

    # 对于中文(一个一个数字)所说年份的处理
    def parse_input_1(self):
        if self.data["year"][0]:
            self.data["year"] = self.data["year"][0].replace(" ", "")
        else:
            self.data["year"] = self.data["year"][1].replace(" ", "")
        if len(self.data["year"]) == 2:
            if self.data["year"] >= "50":
                self.data["year"] = "19" + self.data["year"]
            else:
                self.data["year"] = "20" + self.data["year"]
        self.base_time = datetime(int(self.data["year"]), 1, 1)

    # 表示特定时刻的处理
    def parse_input_2(self):
        second = 0
        if "second" in self.data:
            if self.data["second"]:
                second = int(self.data["second"])
        if not self.data["minute"]:
            self.data["minute"] = 0
        if not (type(self.data["hour"]) == int):
            if self.data["hour"][0]:
                self.data["hour"] = int(self.data["hour"][0])
                if self.data["minute"]:
                    minute_dict = {"钟": 0, "整": 0, "1刻": 15, "半": 30, "3刻": 45}
                    self.data["minute"] = minute_dict[self.data["minute"]]
            else:
                self.data["hour"] = int(self.data["hour"][1])
        if (self.data["hour"] <= 12) and (self.data["hour"] != 0):
            self.is_discrete[1] = 1
            self.period[3] = 3600 * 12
        if self.data["hour"] == 12 or self.data["hour"] == 24:
            self.data["hour"] = 0
        self.base_time = self.now.replace(
            hour=self.data["hour"],
            minute=self.data["minute"],
            second=second,
            microsecond=0,
        )

    # 表示X时刻前/后以及前/后X时刻的处理
    def parse_input_3(self):
        half_delta_dict = {
            "years": relativedelta(months=6),
            "months": relativedelta(days=15),
            "days": relativedelta(hours=12),
            "hours": relativedelta(minutes=30),
            "minutes": relativedelta(seconds=30),
        }
        if self.data["level"] == "years":
            if self.data["years"]:
                delta = relativedelta(years=int(self.data["years"]))
                if "半" in self.entity:
                    delta += half_delta_dict["years"]
            else:
                delta = half_delta_dict["years"]
        elif self.data["level"] == "months":
            if self.data["months"]:
                delta = relativedelta(months=int(self.data["months"]))
                if "半" in self.entity:
                    delta += half_delta_dict["months"]
            else:
                delta = half_delta_dict["months"]
        elif self.data["level"] == "weeks":
            delta = relativedelta(weeks=int(self.data["weeks"]))
        elif self.data["level"] == "days":
            if self.data["days"]:
                delta = relativedelta(days=int(self.data["days"]))
                if "半" in self.entity:
                    delta += half_delta_dict["days"]
            else:
                delta = half_delta_dict["days"]
        elif self.data["level"] == "hours":
            if self.data["hours"]:
                delta = relativedelta(hours=int(self.data["hours"]))
                if "半" in self.entity:
                    delta += half_delta_dict["hours"]
            else:
                delta = half_delta_dict["hours"]
        elif self.data["level"] == "minutes":
            if self.data["minutes"]:
                delta = relativedelta(minutes=int(self.data["minutes"]))
                if "半" in self.entity:
                    delta += half_delta_dict["minutes"]
            else:
                if "1刻钟" in self.entity:
                    delta = relativedelta(minutes=15)
                elif "3刻钟" in self.entity:
                    delta = relativedelta(minutes=45)
                else:
                    delta = half_delta_dict["minutes"]
        else:
            delta = relativedelta(seconds=int(self.data["seconds"]))
        if (self.entity[-1] == "前") or (self.entity[0] == "前"):
            self.base_time = (self.now - delta).replace(microsecond=0)
        elif self.entity[-1] == "后":
            self.base_time = (self.now + delta).replace(microsecond=0)
        else:
            self.base_time = self.now.replace(microsecond=0)
        if any(self.is_range):
            self.duration = [
                delta.years,
                delta.months,
                delta.days,
                delta.hours * 3600 + delta.minutes * 60 + delta.seconds,
            ]

    # 获取本周X日期
    def get_weekday_date(self, weekday):
        weekday -= 1
        result_date = self.now
        while result_date.weekday() != weekday:
            if result_date.weekday() > weekday:
                result_date += relativedelta(days=-1)
            else:
                result_date += relativedelta(days=1)
        return datetime(result_date.year, result_date.month, result_date.day)

    def discrete_week_helper(self):
        self.datetime_level[0], self.datetime_level[1] = 0, 0
        if self.base_time > self.now:
            self.base_time += relativedelta(weeks=-1)
        self.is_discrete[0] = 1
        self.period[2] = 7
        self.is_week = 2

    # 表示相对时刻的处理
    def parse_input_4(self):
        # 相对年表达
        if self.parse_code == 24:
            if self.data["relative"][0]:
                relative_delta = relativedelta(
                    years=self.relative_date_dict[self.data["relative"][0]]
                )
            else:
                relative_delta = relativedelta(
                    years=self.relative_date_dict[self.data["relative"][1]]
                )
            self.base_time += relative_delta
        # 相对月表达
        elif self.parse_code == 25:
            self.base_time += relativedelta(
                months=self.relative_date_dict[self.data["relative"]]
            )
        # 相对周表达
        elif self.parse_code == 26:
            self.base_time = self.get_weekday_date(1)
            if self.data["relative"][0]:
                relative_delta = relativedelta(
                    weeks=self.relative_date_dict[self.data["relative"][0]]
                )
            else:
                relative_delta = relativedelta(
                    weeks=self.relative_date_dict[self.data["relative"][1]]
                )
            self.base_time += relative_delta
        # 相对周末表达
        elif self.parse_code == 27:
            self.base_time = self.get_weekday_date(6)
            if self.data["relative"]:
                self.base_time += relativedelta(
                    weeks=self.relative_date_dict[self.data["relative"]]
                )
            else:
                self.discrete_week_helper()
        # 相对周X(具体日期)表达
        elif self.parse_code == 28:
            if (self.data["weekday"] == "天") or (self.data["weekday"] == "日"):
                self.data["weekday"] = "7"
            self.base_time = self.get_weekday_date(int(self.data["weekday"]))
            if self.data["relative"][1]:
                self.base_time += relativedelta(
                    weeks=self.relative_date_dict[self.data["relative"][1]]
                )
            elif not (self.data["relative"][0]):
                self.discrete_week_helper()
        # 相对日表达
        elif self.parse_code == 29:
            self.base_time += relativedelta(
                days=self.relative_date_dict[self.entity[0:-1]]
            )
        # 相对小时表达
        elif self.parse_code == 34:
            self.base_time += relativedelta(
                hours=self.relative_date_dict[self.entity[0:-2]]
            )
        # 相对小时表达
        elif self.parse_code == 35:
            self.base_time += relativedelta(
                minutes=self.relative_date_dict[self.data["relative"]]
            )
        # 相对小时表达
        elif self.parse_code == 36:
            self.base_time += relativedelta(
                seconds=self.relative_date_dict[self.data["relative"]]
            )

    # 表示一天中特定时间段/点的表达的处理
    def parse_input_5(self):
        if self.parse_code == 32:
            hour = self.time_dict[self.entity]
        elif self.parse_code == 31:
            hour = self.timerange_dict[self.entity][0]
            self.duration[3] = 3600 * self.timerange_dict[self.entity][1]
        else:
            hour = self.datetimerange_dict[self.entity][0]
            self.duration[3] = 3600 * self.datetimerange_dict[self.entity][1]
        self.base_time = self.now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if self.parse_code == 33:
            self.base_time += relativedelta(
                days=self.datetimerange_dict[self.entity][2]
            )

    # 解析日期表述，按需要更新base_time, period, 以及duration字段, 计算出具体输出值以及最接近目前时间的值。
    def parse_input(self):
        if self.parse_code == 30:  # 假期
            self.base_time = self.holiday_dict[self.entity][1]
            if self.base_time > self.now:
                self.value = [
                    self.holiday_dict[self.entity][0],
                    self.holiday_dict[self.entity][1],
                ]
            else:
                self.value = [
                    self.holiday_dict[self.entity][1],
                    self.holiday_dict[self.entity][2],
                ]
        else:
            if self.parse_code in self.parse_dict:
                self.parse_dict[self.parse_code]()
            self.calculate_value()
        self.calculate_nearest()

    def calculate_value(self):
        date_period = relativedelta(
            years=self.period[0], months=self.period[1], days=self.period[2]
        )
        time_period = relativedelta(seconds=self.period[3])
        duration = relativedelta(
            years=self.duration[0],
            months=self.duration[1],
            days=self.duration[2],
            seconds=self.duration[3],
        )
        if any(self.period):
            if any(self.duration):
                self.value = [
                    {"start": self.base_time, "end": self.base_time + duration},
                    {
                        "start": self.base_time + date_period,
                        "end": self.base_time + date_period + duration,
                    },
                ]
            else:
                if any(self.period[0:3]) and self.period[3]:
                    self.value = [
                        self.base_time,
                        self.base_time + time_period,
                        self.base_time + date_period,
                        self.base_time + date_period + time_period,
                    ]
                elif self.period[3]:
                    self.value = [self.base_time, self.base_time + time_period]
                else:
                    self.value = [self.base_time, self.base_time + date_period]
        else:
            if any(self.duration):
                self.value = {"start": self.base_time, "end": self.base_time + duration}
            else:
                self.value = self.base_time

    def calculate_nearest(self):
        if type(self.value) == list:
            if type(self.value[0]) == dict:
                min_delta = abs(self.now - self.value[0]["start"])
            else:
                min_delta = abs(self.now - self.value[0])
            self.nearest = self.value[0]
            for i in range(1, len(self.value)):
                if type(self.value[i]) == dict:
                    temp = abs(self.now - self.value[i]["start"])
                else:
                    temp = abs(self.now - self.value[i])
                if temp <= min_delta:
                    min_delta, self.nearest = temp, self.value[i]
        else:
            self.nearest = self.value


class Duration:
    def __init__(self, entity, parse_code, length):
        self.entity = entity
        self.parse_code = parse_code
        self.type = "Duration"
        self.length = length
        self.value = None
        self.duration_dict = {
            38: 31536000,
            39: 2592000,
            40: 604800,
            41: 86400,
            42: 3600,
            43: 60,
            44: 1,
        }

    def __repr__(self):
        return "{}({}, {}s)".format(self.type, self.entity, self.value)

    # 对于带"半"的时间长度的处理
    def half_duration_helper(self, duration_unit):
        if "年" in self.entity:
            return self.duration_dict[39] * 6
        else:
            return int(0.5 * duration_unit)

    def parse_input(self):
        duration_unit = self.duration_dict[self.parse_code]
        half_offset = 0
        if self.length:
            value = int(self.length)
            if "半" in self.entity:
                half_offset = self.half_duration_helper(duration_unit)
            self.value = value * duration_unit + half_offset
        elif "1刻钟" == self.entity:
            self.value = 15 * 60
        elif "3刻钟" == self.entity:
            self.value = 45 * 60
        else:
            self.value = self.half_duration_helper(duration_unit)


def remove_inclusion(r):
    r = sorted(r, key=lambda x: (x[1], x[2]))
    if len(r) > 1:
        fst = 0
        snd = 1
        while snd < len(r):
            # 重复匹配到的字串a,b，起点相同，比较终点，终点小的被舍弃
            if (r[fst][1] == r[snd][1]) and (r[fst][2] <= r[snd][2]):
                r.remove(r[fst])
            # 起止index有交叉的字串，取起始更小的字串，remove起始较大的字串
            elif (r[fst][1] < r[snd][1]) and (r[fst][2] > r[snd][1]):
                r.remove(r[snd])
            else:
                fst += 1
                snd += 1
    return r


def get_type(
    is_date_range: Optional[int], is_time_range: Optional[int]
) -> Tuple[Optional[str], bool]:
    if is_date_range == 0 and is_time_range is None:
        rtn, is_range = "date", False
    elif is_date_range == 1 and is_time_range is None:
        rtn, is_range = "date", True
    elif is_date_range is None and is_time_range == 0:
        rtn, is_range = "time", False
    elif is_date_range is None and is_time_range == 1:
        rtn, is_range = "time", True
    elif is_date_range == 0 and is_time_range == 0:
        rtn, is_range = "datetime", False
    elif is_date_range is not None and is_time_range == 1:
        rtn, is_range = "datetime", True
    else:
        rtn, is_range = None, False
    return rtn, is_range


def get_datetime_value(data: Union[Dict, datetime]) -> Tuple[datetime, Optional[int]]:
    if isinstance(data, dict):
        value = data["start"]
        delta = int((data["end"] - value).total_seconds())
    else:
        value = data
        delta = None

    return value, delta


class ZHDatetimeExtractor(BaseExtractor):
    def __init__(self, now_func: Callable = None):
        if now_func is None:
            now_func = datetime.now

        self.patterns = {
            # 类似"(年.)月.日"的识别
            re.compile(YEAR_OPTIONAL_DATE): 0,
            # 类似"年.月"的识别
            re.compile(r"(?<!\d)((?:19|20)\d{2})[-./](1[012]|0?[1-9])(?!\d)"): 1,
            # 对于中文(一个一个数字)所说年份的识别，主要针对数字识别模块识别类似二零二零年为2 0 2 0年的问题
            re.compile(r"((?:1\s9|2\s0)(?:\s\d){2})年?|(\d\s\d)年"): 2,
            # 四位阿拉伯数字表示"XXXX年"的识别
            re.compile(f"{YEAR}(?:年)"): 3,
            # 表示"XX月"的识别
            re.compile(r"(1[012]|[1-9])月"): 4,
            # 表示"XX日"的识别
            # re.compile(r"(?<!月)(3[01]|[1-2]\d|(?<!\d)[1-9])[日号]"): 5,
            re.compile(r"(3[01]|[1-2]\d|(?<!\d)[1-9])[日号]"): 5,
            # 表示特定时刻的识别
            re.compile(r"(2[0-4]|1\d|\d)点(钟|1刻|3刻|半|整)?|(2[0-4]|1\d|\d)时"): 6,
            # 表示特定分钟的识别
            re.compile(r"([1-5]\d|0?\s?\d)分"): 7,
            # 表示X点X(分)的识别
            re.compile(r"(2[0-4]|1\d|\d)[点时]([1-5]\d|0?\s?\d)分?"): 8,
            # 表示特定秒钟的识别
            re.compile(r"(0\s?\d|[1-5]\d)秒"): 9,
            # 表示"X年前/后"(时间点)的识别
            re.compile(r"(?:([1-9]\d*)年半?|半年)[前后]"): 10,
            # 表示"X个月前/后"(时间点)的识别
            re.compile(r"(?:([1-9]\d*)个半?月|半个月)[前后]"): 11,
            # 表示"X周前/后"(时间点)的识别
            re.compile(r"([1-9]\d*)(?:个?星期|个?礼拜|周)[前后]"): 12,
            # 表示"X天前/后"(时间点)的识别
            re.compile(r"(?:([1-9]\d*)[天日]半?|半[天日])[前后]"): 13,
            # 表示"X小时前/后"(时间点)的识别
            re.compile(r"(?:([1-9]\d*)(?:小时|个半?小时|个半?钟头)|半个?小时|半个钟头)[前后]"): 14,
            # 表示"X分钟前/后"(时间点)的识别
            re.compile(r"(?:([1-9]\d*)(?:分半钟?|分钟)|半分钟|[13]刻钟)[前后]"): 15,
            # 表示"X秒前/后"(时间点)的识别
            re.compile(r"([1-9]\d*)秒钟?[前后]"): 16,
            # 表示"前/后X年"(时间段)的识别
            re.compile(r"[前后](?:([1-9]\d*)年半?|半年)"): 17,
            # 表示"前/后X个月"(时间段)的识别
            re.compile(r"[前后](?:([1-9]\d*)个半?月|半个月)"): 18,
            # 表示"前/后X周"(时间段)的识别
            re.compile(r"[前后]([1-9]\d*)(?:个?星期|个?礼拜|周)"): 19,
            # 表示"前/后X天"(时间段)的识别
            re.compile(r"[前后](?:([1-9]\d*)[天日]半?|半[天日])"): 20,
            # 表示"前/后X小时"(时间段)的识别
            re.compile(r"[前后](?:([1-9]\d*)(?:小时|个半?小时|个半?钟头)|半个?小时|半个钟头)"): 21,
            # 表示"前/后X分钟"(时间段)的识别
            re.compile(r"[前后](?:([1-9]\d*)(?:分半钟?|分钟)|半分钟|[13]刻钟)"): 22,
            # 表示"前/后X秒"(时间段)的识别
            re.compile(r"[前后]([1-9]\d*)秒钟?"): 23,
            # 表示年级日期的相对表达的识别
            re.compile(
                r"(本|上1|下1|今|去|明|前|后|来|大前|大后)年|(本|这1|这1?个|上1|下1|上1?个|下1?个)年度"
            ): 24,
            # 表示月级日期的相对表达的识别
            re.compile(r"(本|上|下|这1?个|上1?个|下1?个)月"): 25,
            # 表示周级日期的相对表达的识别
            re.compile(
                r"(本|这1?|上1?|下1?|这1?个|上1?个|下1?个)(?:星期|周)|(这1?|上1?|下1?|这1?个|上1?个|下1?个|前个|后个)礼拜"
            ): 26,
            # 表示周末时间段的相对表达的识别
            re.compile(r"(本|这1?|上1?|下1?|这1?个|上1?个|下1?个)?周末"): 27,
            # 表示星期X的相对表达的识别
            re.compile(r"(?:(本周)|(这个?|上个?|下个?)?(?:星期|礼拜|周))([123456天日])"): 28,
            # 表示天级日期的相对表达的识别
            re.compile(r"(?:今|昨|明|前|后|大前|大后)天|[本今昨明]日"): 29,
            # 表示一年中特定日期段的表达的识别
            re.compile(r"元旦|除夕|年30|春节|端午|国庆|中秋|劳动|圣诞|清明"): 30,
            # 表示一天中特定时间段的表达的识别
            re.compile(r"清晨|黎明|早上|早晨|上午|晌午|中午|午间|午后|下午|黄昏|晚上|夜晚|晚间|傍晚|深夜|凌晨"): 31,
            # 表示一天中特定时间点的表达的识别
            re.compile(r"正午|半夜|午夜"): 32,
            # 天级日期和特定时间段在一起时的缩写表达的识别
            re.compile(r"今早|今晚|今夜|昨晚|昨夜|明早|明晚"): 33,
            # 表示小时级时间的相对表达的识别
            re.compile(r"(?:这1|上1|下1|这1?个|上1?个|下1?个)小时|(?:这1?个|上1?个|下1?个)钟头"): 34,
            # 表示分钟级时间的相对表达的识别
            re.compile(r"(这1|上1|下1)分钟"): 35,
            # 表示秒钟级时间的相对表达的识别
            re.compile(r"(这1|上1|下1)秒钟?"): 36,
            # 表示"现在"的表达的识别
            re.compile(r"现在|当下|刚刚|此时此刻|此时|此刻|目前|当前|今时"): 37,
            # 表示"X年"(时间长度)的处理
            re.compile(r"([1-9]\d{0,2}|[1-9]\d{4,}|1[0-8]\d{2}|2[1-9]\d{2})年半?|半年"): 38,
            # 表示"X个月"(时间长度)的处理
            re.compile(r"([1-9]\d*)个半?月|半个月"): 39,
            # 表示"X周"(时间长度)的处理
            re.compile(r"([1-9]\d*)(?:个?星期|个?礼拜|周)"): 40,
            # 表示"X天"(时间长度)的处理
            re.compile(r"([1-9]\d*)[天日]半?|半[天日]"): 41,
            # 表达"X小时"(时间长度)的表达
            re.compile(r"(?:([1-9]\d*)(?:小时|个半?小时|个半?钟头)|半个?小时|半个钟头)"): 42,
            # 表达"X分钟"(时间长度)的表达
            re.compile(r"([1-9]\d*)分[钟半]|[13]刻钟|半分钟"): 43,
            # 表达"X秒钟"(时间长度)的表达
            re.compile(r"([1-9]\d*)秒钟?"): 44,
            # 形如XX:XX:XX的表达(表示时间)的识别
            re.compile(r"(2[0-4]|1\d|\d)[:：](0\d|[1-5]\d)(?:[:：](0\d|[1-5]\d))?"): 45,
            # 表达"xx月xx"
            re.compile(r"([2-9]|1[0-2]?)月(3[01]|[1-2]\d|[1-9])[日]?"): 46,
        }
        self.now_func = now_func

    def parse(self, text: Text, *args: Any) -> List[Datetime]:
        # s_arabic_without_dot: 中文数字转换为阿拉伯数字 (不替换"点")
        (
            s_arabic_without_dot,
            replacement_relationship_without_dot,
            space_index,
        ) = number_ext.parse_datetime_num(text)
        # 当前时间
        now = self.now_func()
        # 识别结果
        r = []
        durations = []

        # 去掉空格
        # s_arabic_without_dot = s_arabic_without_dot.replace(" ", "")

        for (pattern, parse_code) in self.patterns.items():
            matches = pattern.finditer(s_arabic_without_dot)
            for match in matches:
                if parse_code == 0:
                    date_res = match.group(0)
                    year = match.group("year")
                    month = match.group("month")
                    day = match.group("day")
                    r.append(
                        (
                            DateObject(
                                now,
                                date_res,
                                parse_code,
                                [1, 1, 1, 0, 0, 0],
                                [0, None],
                                [0, None],
                                "Date",
                                year=year,
                                month=month,
                                day=day,
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 1:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                datetime(int(match.group(1)), int(match.group(2)), 1),
                                duration=(0, 1, 0, 0),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 2:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 0, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                duration=(1, 0, 0, 0),
                                year=(match.group(1), match.group(2)),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 3:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 0, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                datetime(int(match.group("year")), 1, 1),
                                duration=(1, 0, 0, 0),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 4:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 1, 0, 0, 0, 0],
                                [1, None],
                                [1, None],
                                "DateRange",
                                datetime(now.year, int(match.group(1)), 1),
                                (1, 0, 0, 0),
                                (0, 1, 0, 0),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 5:
                    # 针对类似31号的问题，这里如果日期超过当月最大日，需要减少月份
                    period = (0, 1, 0, 0)
                    try:
                        base_time = datetime(now.year, now.month, int(match.group(1)))
                    except ValueError as e:
                        if e.args[0] == "day is out of range for month":
                            # 报错出在小月，而每个小月前后都是大月
                            base_time = datetime(
                                now.year, now.month - 1, int(match.group(1))
                            )
                            period = (0, 2, 0, 0)
                        else:
                            raise
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 1, 0, 0, 0],
                                [1, None],
                                [0, None],
                                "Date",
                                base_time,
                                period,
                            ),
                            match.start(),
                            match.end(),
                        )
                    )

                elif parse_code == 6:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 1, 1, 0],
                                [None, 0],
                                [None, 0],
                                "Time",
                                hour=(match.group(1), match.group(3)),
                                minute=match.group(2),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 7:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 0, 1, 0],
                                [None, 1],
                                [None, 0],
                                "Time",
                                now.replace(
                                    minute=int(match.group(1).replace(" ", "")),
                                    second=0,
                                    microsecond=0,
                                ),
                                (0, 0, 0, 3600),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 8:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 1, 1, 0],
                                [None, 0],
                                [None, 0],
                                "Time",
                                hour=int(match.group(1)),
                                minute=int(match.group(2).replace(" ", "")),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 9:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 0, 0, 1],
                                [None, 1],
                                [None, 0],
                                "Time",
                                now.replace(
                                    second=int(match.group(1).replace(" ", "")),
                                    microsecond=0,
                                ),
                                (0, 0, 0, 60),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 10:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, None],
                                [0, None],
                                "Date",
                                level="years",
                                years=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 11:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, None],
                                [0, None],
                                "Date",
                                level="months",
                                months=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 12:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, None],
                                [0, None],
                                "Date",
                                level="weeks",
                                weeks=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 13:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 0],
                                "Datetime",
                                level="days",
                                days=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 14:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 0],
                                "Datetime",
                                level="hours",
                                hours=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 15:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 0],
                                "Datetime",
                                level="minutes",
                                minutes=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 16:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 0],
                                "Datetime",
                                level="seconds",
                                seconds=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 17:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, None],
                                [1, None],
                                "DateRange",
                                level="years",
                                years=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 18:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, None],
                                [1, None],
                                "DateRange",
                                level="months",
                                months=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 19:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, None],
                                [1, None],
                                "DateRange",
                                level="weeks",
                                weeks=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 20:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                level="days",
                                days=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 21:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                level="hours",
                                hours=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 22:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                level="minutes",
                                minutes=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 23:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                level="seconds",
                                seconds=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 24:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 0, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                datetime(now.year, 1, 1),
                                duration=(1, 0, 0, 0),
                                relative=(match.group(1), match.group(2)),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 25:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                datetime(now.year, now.month, 1),
                                duration=(0, 1, 0, 0),
                                relative=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 26:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                duration=(0, 0, 7, 0),
                                is_week=1,
                                relative=(match.group(1), match.group(2)),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 27:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 0, 0, 0, 0],
                                [0, None],
                                [1, None],
                                "DateRange",
                                duration=(0, 0, 2, 0),
                                relative=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 28:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 0, 0, 0],
                                [0, None],
                                [0, None],
                                "Date",
                                relative=(match.group(1), match.group(2)),
                                weekday=match.group(3),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 29:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 0, 0, 0],
                                [0, None],
                                [0, None],
                                "Date",
                                datetime(now.year, now.month, now.day),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 30:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 1, 1, 0, 0, 0],
                                [1, None],
                                [0, None],
                                "Date",
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 31:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 1, 0, 0],
                                [None, 0],
                                [None, 1],
                                "TimeRange",
                                is_specific_time=1,
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 32:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 1, 0, 0],
                                [None, 0],
                                [None, 0],
                                "Time",
                                is_specific_time=1,
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 33:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 0, 0],
                                [None, 0],
                                [None, 1],
                                "DatetimeRange",
                                is_specific_time=1,
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 34:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 0, 0],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                now.replace(minute=0, second=0, microsecond=0),
                                duration=(0, 0, 0, 3600),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 35:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 0],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                now.replace(second=0, microsecond=0),
                                duration=(0, 0, 0, 60),
                                relative=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 36:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 1],
                                "DatetimeRange",
                                now.replace(microsecond=0),
                                duration=(0, 0, 0, 1),
                                relative=match.group(1),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 37:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [1, 1, 1, 1, 1, 1],
                                [0, 0],
                                [0, 0],
                                "Datetime",
                                now.replace(microsecond=0),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif (parse_code >= 38) and (parse_code <= 44):
                    durations.append(
                        (
                            Duration(match.group(0), parse_code, match.group(1)),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 45:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 0, 0, 1, 1, 0],
                                [None, 0],
                                [None, 0],
                                "Time",
                                hour=int(match.group(1)),
                                minute=int(match.group(2)),
                                second=match.group(3),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )
                elif parse_code == 46:
                    r.append(
                        (
                            DateObject(
                                now,
                                match.group(0),
                                parse_code,
                                [0, 1, 1, 0, 0, 0],
                                [1, None],
                                [0, None],
                                "Date",
                                datetime(
                                    now.year, int(match.group(1)), int(match.group(2))
                                ),
                            ),
                            match.start(),
                            match.end(),
                        )
                    )

        r = remove_inclusion(r)
        for (date_object, _, _) in r:
            date_object.parse_input()
        for (duration, _, _) in durations:
            duration.parse_input()
        # 将表达连续时间子串尝试进行合并
        if len(r) >= 2:
            i, j = 0, 1
            while j < len(r):
                fst = r[i]
                snd = r[j]
                # 如果两个时间表达是连着的
                if fst[2] == snd[1]:
                    sum_date_object = fst[0] + snd[0]
                    if sum_date_object:
                        if sum_date_object == "Illegal":
                            r.remove(r[j])
                            r.remove(r[i])
                        else:
                            r[i] = (fst[0] + snd[0], fst[1], snd[2])
                            r.remove(r[j])
                    else:
                        i += 1
                        j += 1
                else:
                    i += 1
                    j += 1
        r += durations
        r = remove_inclusion(r)

        i = 0
        # 将转换为阿拉伯数字的entity转换成中文数字的entity
        for (obj, start, end) in r:
            shift = 0
            while i < len(replacement_relationship_without_dot):
                (
                    origin,
                    _,
                    _,
                    now,
                    start_,
                    end_,
                ) = replacement_relationship_without_dot[i]
                if end_ <= end:
                    if (start_ == start - 1) and (now[0] == " "):
                        obj.entity = origin + obj.entity[end_ - start :]
                        shift += len(origin) - len(now) + 1
                        i += 1
                    elif start_ >= start:
                        obj.entity = (
                            obj.entity[: (start_ - start + shift)]
                            + origin
                            + obj.entity[(end_ - start + shift) :]
                        )
                        shift += len(origin) - len(now)
                        i += 1
                    else:
                        i += 1
                else:
                    break
            if obj.parse_code == 2:
                obj.entity = "".join(obj.entity.split())
            if i == len(replacement_relationship_without_dot):
                break

        date_objects = []
        # 构造输出的数据结构
        for (obj, _, _) in r:
            is_duration = type(obj) == Duration
            is_multivalue = isinstance(obj.value, list)

            if is_duration:
                datetime_level = [0, 0, 0, 0, 0, 1]
                date_type, is_range = "duration", True
                if is_multivalue:
                    values = [{"value": None, "delta": v} for v in obj.value]
                else:
                    values = [{"value": None, "delta": obj.value}]

            else:
                datetime_level = obj.datetime_level
                date_type, is_range = get_type(obj.is_range[0], obj.is_range[1])
                if is_multivalue:
                    values = []
                    for v in obj.value:
                        value, delta = get_datetime_value(v)
                        values.append({"value": value, "delta": delta})
                else:
                    value, delta = get_datetime_value(obj.value)
                    values = [{"value": value, "delta": delta}]

            try:
                search_rtn = re.search(obj.entity, text)
                start_pos = search_rtn.start()
                end_pos = search_rtn.end()
            except AttributeError:
                # re.search could find None if some unexpected errors happened,
                # and this will cause AttributeError when try to call None's start() method
                raise
            else:
                date_objects.append(
                    Datetime(
                        **{
                            "entity": obj.entity,
                            "start_pos": start_pos,
                            "end_pos": end_pos,
                            "type": date_type,
                            "is_range": is_range,
                            "is_multivalue": is_multivalue,
                            "values": values,
                            "datetime_level": datetime_level,
                        }
                    )
                )

        return date_objects


date_extractor = ZHDatetimeExtractor()

if __name__ == "__main__":
    num = 100
    while True:
        print(date_extractor.parse(input()))
