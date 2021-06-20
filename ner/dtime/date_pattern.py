"""
注：模块内使用了重复的named group，re标准模块不支持这种写法，因此需要使用regex替代标准re
"""

# ------------------ date --------------------------- #
# 日期分隔符
DATE_SPLIT = r"[-/.]"
_ = DATE_SPLIT

# 普通年份
YEAR = r"(?P<year>(?:18|19|20)[0-9]{2})"
# 闰年
LEAP_YEAR = r"(?P<year>(?:(?:18|19|20)(?:04|08|[2468][048]|[13579][26]))|2000)"
# 分隔符+年
YEAR_SPLIT = r"[-/.年]"
y_ = YEAR_SPLIT
# 分隔符+月
MON_SPLIT = r"[-/.月]"
m_ = MON_SPLIT
# 日
DAY_UNIT = r"[日号]"
# OPT_DAY_UNIT = fr"{DAY_UNIT}?"
OPT_DAY_UNIT = fr"(?:{DAY_UNIT}|(?!\d))"  # 如果不带"日|号"，则后不能跟数字

# 所有月份
MON = r"(?P<month>0?[1-9]|1[0-2])"
# 大月月份:
BIG_MON = r"(?P<month>0?[13578]|1[02])"
# 小月月份
SMALL_MON = r"(?P<month>0?[469]|11)"
# 二月
MONTH2 = r"(?P<month>0?2)"

# 日的表达后面正向不匹配数字
# 平年2月日的表达
NORMAL_MON2_DAY = fr"(?P<day>1[0-9]|2[0-8]|0?[1-9]){OPT_DAY_UNIT}"
# 29日的表达
DAY29 = fr"(?P<day>29){OPT_DAY_UNIT}"
# 大月的日表达
BIG_MON_DAY = fr"(?P<day>[12][0-9]|3[01]|0?[1-9]){OPT_DAY_UNIT}"
# 小月的日表达
SMALL_MON_DAY = fr"(?P<day>[12][0-9]|30|0?[1-9]){OPT_DAY_UNIT}"

# 大月日期（无2月29日）
BIG_MON_DATE = fr"{YEAR}{y_}{BIG_MON}{m_}{BIG_MON_DAY}"
# 小月日期（无2月29日）
SMALL_MON_DATE = fr"{YEAR}{y_}{SMALL_MON}{m_}{SMALL_MON_DAY}"
# 闰年2月日期（闰年情况包含2月29）
LEAP_MON2_DATE = fr"{LEAP_YEAR}{y_}{MONTH2}{m_}"

NORMAL_DATE = fr"{YEAR}{y_}({BIG_MON}{m_}{BIG_MON_DAY}|{SMALL_MON}{m_}{SMALL_MON_DAY}|{MONTH2}{m_}{NORMAL_MON2_DAY})"

LEAP_DATE29 = fr"{LEAP_YEAR}{y_}{MONTH2}{m_}{DAY29}"

# 标准日期表达
DATE_RE = fr"((?<!\d){NORMAL_DATE}|{LEAP_DATE29})"

# [年]月日(可不带年的日期表达，小月不能超过30日，2月不能超过28日，日期前后不能带数字)
YEAR_OPTIONAL_DATE = fr"(?<!\d)(?:(?:{YEAR}{y_})?(?:{BIG_MON}{m_}{BIG_MON_DAY}|{SMALL_MON}{m_}{SMALL_MON_DAY}|" \
                     f"{MONTH2}{m_}{NORMAL_MON2_DAY})|{LEAP_YEAR}{y_}{MONTH2}{m_}{DAY29})"

# 年月
YEAR_MONTH = fr"(?<!\d){YEAR}{y_}{MON}(?:{m_}|(?!\d))"
# 年
YEAR_RE = fr"(?<!\d){YEAR}(?:{y_}|(?!\d))"
# 月
MONTH_RE = fr"(?<!\d){MON}[月]"
# 日
DAY_RE = fr"(?<!\d)(?P<day>[12][0-9]|3[01]|0?[1-9]){DAY_UNIT}"

DATE_ALL = fr"{YEAR_OPTIONAL_DATE}|{YEAR_MONTH}|{YEAR_RE}|{MONTH_RE}|{DAY_RE}"


# ------------------ time --------------------------- #
TIME_SPLIT = fr"[- .:：]"
t_ = TIME_SPLIT
HOUR = r"(?P<hour>2[0-3]|1\d|\d)"
HOUR_UNIT = r"(?:点|时)"
HOUR_SPLIT = fr"(?:[- .:：]|{HOUR_UNIT})"
h_ = HOUR_SPLIT
MINUTE = r"(?P<minute>0?\d|[1-5]\d)"
MINUTE_UNIT = r"[分]"
MINUTE_SPLIT = fr"(?:[- .:：]|{MINUTE_UNIT})"
min_ = MINUTE_SPLIT
SECONDS = r"(?P<seconds>0?\d|[1-5]\d)"
SEC_UNIT = fr"[秒]"
OPT_SEC_UNIT = fr"(?:{SEC_UNIT}|(?!\d))"

# x点
TIME_RE1 = fr"{HOUR}{HOUR_UNIT}"
# x点x[分]
TIME_RE2 = fr"{HOUR}{h_}{MINUTE}(?:{MINUTE_UNIT}|(?!\d))"
# x点x分x[秒]
TIME_RE3 = fr"{HOUR}{h_}{MINUTE}{min_}{SECONDS}{OPT_SEC_UNIT}"
# 时间的表达 x点[x分[x秒]]
TIME_ALL = fr"({TIME_RE3}|{TIME_RE2}|{TIME_RE1})"


# 特定时刻的识别
TIME_SCALE = fr"{HOUR}(?:点|时)(?:1刻|3刻|半|整|钟整|钟)"

# ------------------ datetime --------------------------- #
DATETIME_ALL = fr"{DATE_ALL}{TIME_ALL}|{TIME_ALL}|{DATE_ALL}"


if __name__ == '__main__':
    import regex as re
    # 测试 DATE_ALL
    data_list = [
        ("2020.2.29", (2020, 2, 29)),
        ("2020.2月29", (2020, 2, 29)),
        ("2020/6/03", (2020, 6, 3)),
        ("6.30", (None, 6, 30)),
        ("2.28", (None, 2, 28)),
        ("03月5日", (None, 3, 5)),
        ("3月31", (None, 3, 31)),
        ("206.30", []),
        ("2020年5月8日", (2020, 5, 8)),
        ("2020年1月", (2020, 1, None)),
        ("2020.2", (2020, 2, None)),
        ("2018.3月", (2018, 3, None)),
        ("2017年4", (2017, 4, None)),
        ("2016/12", (2016, 12, None)),
        ("2015-11", (2015, 11, None)),
        ("2020", (2020, None, None)),
        ("2020年", (2020, None, None)),
        ("2020.", (2020, None, None)),
        ("2018.", (2018, None, None)),
        ("2017年", (2017, None, None)),
        ("2016/", (2016, None, None)),
        ("2015-", (2015, None, None)),
        ("20151", []),
        ("12015", []),
        ("5", []),
        ("1月", (None, 1, None)),
        ("12月", (None, 12, None)),
        ("1", []),
        ("01日", (None, None, 1)),
        ("1号", (None, None, 1)),
        ("31日", (None, None, 31)),
        ("19号", (None, None, 19)),
        ("25日", (None, None, 25)),
        ("325日", [])
    ]
    pt = re.compile(DATE_ALL)
    for dt, res in data_list:
        rtn = [(i.group("year"), i.group("month"), i.group("day")) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        print(rtn)
        assert rtn == res
    # 测试YEAR_OPTIONAL_DATE
    date_list = [
        ("2020.2.29", (2020, 2, 29)),
        ("2020.2月29", (2020, 2, 29)),
        ("2021.2.29", []),
        ("12000.2.29", []),
        ("1991.12.16", (1991, 12, 16)),
        # ("11991.12.16", False),
        ("2020.6.31", []),
        ("2019/10/07", (2019, 10, 7)),
        ("6.30", (None, 6, 30)),
        ("6.31", []),
        ("2.29", []),
        ("2月29日", []),
        ("2.28", (None, 2, 28)),
        ("206.30", []),
        ("2020年5月8日", (2020, 5, 8)),
        ("5月8日", (None, 5, 8)),
        ("5月8", (None, 5, 8)),
        ("6月31日", []),
        ("2020.2.3日1", (2020, 2, 3)),
        ("2020.2.031", [])
    ]
    # print(YEAR_OPTIONAL_DATE)
    pt = re.compile(YEAR_OPTIONAL_DATE)
    for dt, res in date_list:
        rtn = [(i.group("year"), i.group("month"), i.group("day")) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        print(rtn)
        assert rtn == res

    # 测试YEAR_MONTH
    date_list = [
        ("2020.5.8", (2020, 5)),
        ("2020年1月", (2020, 1)),
        ("2020.2", (2020, 2)),
        ("2018.3月", (2018, 3)),
        ("2017年4", (2017, 4)),
        ("2016/12", (2016, 12)),
        ("2015-11", (2015, 11))
    ]
    pt = re.compile(YEAR_MONTH)
    for dt, res in date_list:
        rtn = [(i.group("year"), i.group("month")) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        # print(rtn)
        assert rtn == res

    # 测试YEAR_RE
    date_list = [
        ("2020", (2020, )),
        ("2020年", (2020, )),
        ("2020.", (2020, )),
        ("2018.", (2018, )),
        ("2017年", (2017, )),
        ("2016/", (2016, )),
        ("2015-", (2015, )),
        ("20151", []),
        ("12015", [])
    ]
    pt = re.compile(YEAR_RE)
    for dt, res in date_list:
        rtn = [(i.group("year"), ) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        # print(rtn)
        assert rtn == res

    # 测试MONTH_RE
    date_list = [
        ("5", []),
        ("1月", (1,)),
        ("2", []),
        ("3月", (3,)),
        ("12月", (12,)),
    ]
    pt = re.compile(MONTH_RE)
    for dt, res in date_list:
        rtn = [(i.group("month"),) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        # print(rtn)
        assert rtn == res

    # 测试DAY_RE
    date_list = [
        ("1", []),
        ("01日", (1,)),
        ("1号", (1,)),
        ("31日", (31,)),
        ("19号", (19,)),
        ("25日", (25,)),
        ("325日", [])
    ]
    pt = re.compile(DAY_RE)
    for dt, res in date_list:
        rtn = [(i.group("day"),) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        # print(rtn)
        assert rtn == res

    # 测试TIME_RE
    data_list = [
        ("12点", (12, None, None)),
        ("12点", (12, None, None)),
        ("8点", (8, None, None)),
        ("23点59分", (23, 59, None)),
        ("1点59", (1, 59, None)),
        ("06:15", (6, 15, None)),
        ("08:05:59", (8, 5, 59)),
        ("12.15.05", (12, 15, 5)),
        ("12-15-05", (12, 15, 5)),
        ("12点15分361", (12, 15, None)),
        ("12点151", (12, None, None)),
    ]
    pt = re.compile(TIME_ALL)
    for dt, res in data_list:
        rtn = [(i.group("hour"), i.group("minute"), i.group("seconds")) for i in pt.finditer(dt)]
        if rtn:
            rtn = tuple([int(i) if i else None for i in rtn[0]])
        else:
            rtn = []
        # print(rtn)
        assert rtn == res

    # test TIME_SCALE
    data_list = [
        ("23点整", 23, "23点整"),
        ("13点钟整", 13, "13点钟整"),
        ("12点3刻", 12, "12点3刻"),
        ("05点半", 5, "5点半"),
        ("3点1刻", 3, "3点1刻"),
        ("5时3刻", 5, "5时3刻"),

    ]
    pt = re.compile(TIME_SCALE)
    for dt, rtn, et in data_list:
        res = [(i.group("hour"), i.group(0)) for i in pt.finditer(dt)][0]
        num, entity = res
        print(rtn, entity)
        assert rtn == int(num)
        assert entity == et
