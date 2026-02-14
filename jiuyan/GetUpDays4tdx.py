from mootdx.quotes import Quotes
from mootdx.server import bestip


class TdxQuotes:
    def __init__(self):
        bestip(console=True)
        self.client = Quotes.factory(market='std', bestip=True)

    # 计算涨停状态并统计连板天数
    @staticmethod
    def _calculate_limit_up_days(code, df):
        """计算连续涨停天数"""
        if df.empty:
            return 0

        # 1. 计算涨停条件：
        df['prev_close'] = df['close'].shift(1)  # 前一日收盘价
        if code.startswith('30') or code.startswith('688'):
            # 当日收盘价 ≥ 前日收盘价 * 1.194（近似20%涨停）
            df['is_limit_up'] = (df['close'] >= df['prev_close'] * 1.194).astype(int)
        else:
            # 当日收盘价 ≥ 前日收盘价 * 1.097（近似10%涨停）
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

    def _get_limit_up_streak(self, code):
        """获取指定股票的连板天数"""
        # df = reader.daily(symbol=code)
        df = self.client.bars(symbol=code, frequency=9, offset=10)
        if df.empty:
            return 0
        return self._calculate_limit_up_days(code, df)

    # 获取涨停天数
    def get_up_days(self, code):
        return self._get_limit_up_streak(code)

if __name__ == '__main__':
    tdx = TdxQuotes()
    print(tdx.get_up_days('300411'))