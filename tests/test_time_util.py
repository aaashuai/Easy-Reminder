from utils import TimeUtil


def test_time_util():
    assert TimeUtil.seconds2date_str(15) == '15秒', TimeUtil.seconds2date_str(15)
    assert TimeUtil.seconds2date_str(61) == '1分1秒', TimeUtil.seconds2date_str(61)
    assert TimeUtil.seconds2date_str(3661) == '1时1分1秒', TimeUtil.seconds2date_str(3661)
    assert TimeUtil.seconds2date_str(90061) == '1天1时1分1秒', TimeUtil.seconds2date_str(90061)


if __name__ == '__main__':
    test_time_util()