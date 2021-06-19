import datetime
from typing import Optional


from logger import logger


def extract_time(text: str) -> Optional[int]:
    res = extractor().extract_time(text)
    # logger.info(f"extract result: {res}")
    if not res:
        return
    print(res)
    return int(datetime.datetime.strptime(res[0]["keyDate"], "%Y-%m-%d %H:%M:%S").timestamp())


if __name__ == '__main__':
    print(extract_time("今天上午9点"))
