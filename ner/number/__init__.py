from typing import List, Any, Tuple, Text
from typing import Union

from ner.number.extractors import ZHCustomizedExtractor, DatetimeIntegerExtractor
from ner.models import Number
from recognizers_number import ModelResult, regex
from recognizers_number import NumberRecognizer, Culture, AgnosticNumberParserFactory, ParserType, \
    ChineseNumberParserConfiguration, NumberModel, Model

from ner.number.custom_numeric import CustomNumeric


from ner import BaseExtractor

__all__ = ("ZHNumberExtractor", "number_ext")


def replace_by_index_range(text: str, r_start: int, r_end: int, replace_text: Union[str, int, float]):
    return text[:r_start] + str(replace_text) + text[r_end + 1:]


def transfer2num(text: str, result: List[ModelResult]):
    # 将格式转换为 eg:('12点15', [('十二', 0, 1, '12', 0, 1), ('十五', 3, 4, '15', 3, 4)])
    rtn = []
    total_len_diff = 0
    for r in result:
        value = str(r.resolution["value"])
        len_diff = 0
        # 获取数字和汉字的长度差，并据此对汉字进行替换，及计算替换后的数字位置
        len_diff += len(value) - len(r.text)

        num_st, num_ed = r.start + total_len_diff, r.end + total_len_diff + len_diff
        text = replace_by_index_range(text, r.start + total_len_diff, r.end + total_len_diff, value)
        total_len_diff += len_diff
        # 为了方便替换对end index+1
        rtn.append((r.text, r.start, r.end + 1, value, num_st, num_ed + 1))
    return text, rtn


def special_insert_space(text: str):
    """
    预处理过程，主要是针对用户输入的两个独立汉字数字之间插入空格：
    正则"[一~九](?=[零-九])"的情况需要插入空格
    且一九xx年，二零xx年，类似这种每一位都要加空格
    :param text:
    :return:
    """
    # 在两个数字间插入空格
    space_index = []
    pattern = f'{CustomNumeric.ZeroOnly}(?={CustomNumeric.ZeroToNineIntegerRegex}{CustomNumeric.ZeroToNineIntegerRegex}年)' \
              f'|{CustomNumeric.ZeroOnly}(?={CustomNumeric.ZeroToNineIntegerRegex}年)' \
              f'|{CustomNumeric.OneToNineIntegerRegex}(?={CustomNumeric.ZeroToNineIntegerRegex})'
    for i in regex.finditer(pattern, text):
        start, end = i.span()
        # 已插入的空行需要被增加入下次index
        space_len = len(space_index)
        text = text[:end + space_len] + " " + text[end + space_len:]
        space_index.append(end + space_len)
    return text, space_index


class ZHNumberRecognizer(NumberRecognizer):
    def initialize_configuration(self):
        super(ZHNumberRecognizer, self).initialize_configuration()
        # region Mrs
        self.register_model('ZHNumberModel', Culture.Chinese, lambda options: NumberModel(
            AgnosticNumberParserFactory.get_parser(
                ParserType.NUMBER, ChineseNumberParserConfiguration()),
            ZHCustomizedExtractor()
        ))
        # number model for datetime
        self.register_model('DatetimeNumberModel', Culture.Chinese, lambda options: NumberModel(
            AgnosticNumberParserFactory.get_parser(
                ParserType.NUMBER, ChineseNumberParserConfiguration()),
            DatetimeIntegerExtractor()
        ))

    def get_number_model(self, culture: str = None, fallback_to_default_culture: bool = True) -> Model:
        return self.get_model('ZHNumberModel', culture, fallback_to_default_culture)

    def get_datetime_num_model(self, culture: str = None, fallback_to_default_culture: bool = True) -> Model:
        return self.get_model('DatetimeNumberModel', culture, fallback_to_default_culture)


class ZHNumberExtractor(BaseExtractor):
    def __init__(self):
        recognizer = ZHNumberRecognizer(Culture.Chinese)
        self.model = recognizer.get_number_model()
        self.datetime_model = recognizer.get_datetime_num_model()

    def parse(self, text, *args: Any) -> List[Number]:
        result = self.model.parse(text)
        rtn = []
        for i in result:
            value = i.resolution["value"]
            rtn.append(Number(entity=i.text, start_pos=i.start, end_pos=i.end+1, num=value))
        return rtn

    def parse_datetime_num(self, text) -> Tuple[Text, List, List]:
        # TODO insert space could make error to some special entities
        processed_text, space_index = special_insert_space(text)
        result = self.datetime_model.parse(processed_text)
        text, rtn = transfer2num(processed_text, result)
        return text, rtn, space_index


number_ext = ZHNumberExtractor()


if __name__ == '__main__':
    ext = ZHNumberExtractor()
    while True:
        print([i.dict() for i in ext.parse(input())])
