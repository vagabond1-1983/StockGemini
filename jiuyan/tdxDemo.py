# from mootdx.reader import Reader
#
# reader = Reader.factory(market='ext', tdxdir='D:\\softwares\\tdx')

from mootdx.quotes import Quotes

client = Quotes.factory(market='std')
# print(client.bars(symbol='002645', frequency=9, offset=10))

# 计算涨停状态并统计连板天数
def calculate_limit_up_days(df):
    """计算连续涨停天数"""
    if df.empty:
        return 0

    # 1. 计算涨停条件：当日收盘价 ≥ 前日收盘价 * 1.097（近似10%涨停）
    df['prev_close'] = df['close'].shift(1)  # 前一日收盘价
    df['is_limit_up'] = (df['close'] >= df['prev_close'] * 1.097).astype(int)  # [2](@ref)

    # 2. 统计连续涨停天数
    current_streak = 0
    max_streak = 0
    for is_up in df['is_limit_up']:
        if is_up == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0  # 中断重置
    return current_streak

def get_limit_up_streak(code):
    """获取指定股票的连板天数"""
    # df = reader.daily(symbol=code)
    df = client.bars(symbol=code, frequency=9, offset=10)
    if df.empty:
        return 0
    return calculate_limit_up_days(df)

# 读取日线数据
# print(get_limit_up_streak('002645'))

company_info = client.F10(symbol='002645')['公司概况']
print(company_info)
company_info = client.F10(symbol='600635')['公司概况']
print(company_info)
import re
pattern = r'002645\s+([\u4e00-\u9fa5]+) 更新日期'
company_name = re.search(pattern, company_info)
if company_name:
    print(company_name.group(1))