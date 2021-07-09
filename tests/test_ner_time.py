import pytest

from datetime import datetime
from utils import NerUtil, TimeUtil
from typing import Union


def ner_time_interactively():
    ner = NerUtil()

    while True:
        print('-'*30)
        try:
            txt = input("date: ")
            job_type, next_run_time, period_type = ner.extract_time(txt)
            print(job_type.name)
            print(TimeUtil.timestamp2datetime(next_run_time))
            print(period_type)
        except Exception as e:
            print(str(e))

    # while True:
    #     print("-" * 30)
    #     try:
    #         txt = input("number: ")
    #         print(ner.extract_number(txt))
    #     except Exception as e:
    #         print(str(e))
    #

def test_extract_schedule(mocker):
    d_wed = datetime.strptime("2021-07-07 15:00:00", "%Y-%m-%d %H:%M:%S")
    mocker.patch.object(TimeUtil, "now_datetime", lambda: d_wed)
    ner = NerUtil()

    def assert_one(text: str, d_time_str: str, e_type: Union[str, int]):
        timestamp = TimeUtil.datetime2timestamp(d_time_str)
        assert ner.extract_time(text) == (
            timestamp,
            e_type,
        ), f"result: {ner.extract_time(text)}"

    # test monthly
    assert_one("每月三号下午六点", "2021-08-03 18:00:00", "monthly")
    assert_one("每月10号下午六点", "2021-07-10 18:00:00", "monthly")

    # test yearly
    assert_one("每年一月三号下午六点", "2022-01-03 18:00:00", "yearly")
    assert_one("每年七月10号下午六点", "2021-07-10 18:00:00", "yearly")

    # test weekly
    assert_one("每周三下午六点", "2021-07-07 18:00:00", "weekly")
    assert_one("每周三下午两点", "2021-07-14 14:00:00", "weekly")
    assert_one("每周二下午两点", "2021-07-13 14:00:00", "weekly")
    assert_one("每周四下午两点", "2021-07-08 14:00:00", "weekly")

    # test daily
    assert_one("每天下午两点", "2021-07-08 14:00:00", "daily")
    assert_one("每天下午四点", "2021-07-07 16:00:00", "daily")
    # test days
    assert_one("每3天", "2021-07-10 15:00:00", 3)


if __name__ == "__main__":
    pytest.main([__file__])
    # ner_time_interactively()
