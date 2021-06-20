from recognizers_number import ChineseNumeric


class CustomNumeric(ChineseNumeric):
    OneToNineIntegerRegex = f'[一二三四五六七八九壹贰貳叁肆伍陆陸柒捌玖两兩俩倆仨]'
    ZeroOnly = f'[零〇]'
    YearDate = f'{OneToNineIntegerRegex}{ChineseNumeric.ZeroToNineIntegerRegex}{ChineseNumeric.ZeroToNineIntegerRegex}{ChineseNumeric.ZeroToNineIntegerRegex}(?=年)'
    MinuteRegex = f'(?<=[点點]){ZeroOnly}{OneToNineIntegerRegex}'
    WeekNum = f'(?<=周){OneToNineIntegerRegex}'
