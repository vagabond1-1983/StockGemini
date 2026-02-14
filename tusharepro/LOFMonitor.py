import pandas as pd
import tushare as ts
import numpy as np

token = '8ieskv7fheqqpctiek'
pro = ts.pro_api()
pro._DataApi__token = token
pro._DataApi__http_url = 'http://tushare.top/dataapi'

start_date = '20260101'
end_date = '20260109'
cost = 0.015


# 获取 LOF 基金列表
def get_lof_funds():
    # market='E' 表示 ETF 和 LOF，fund_type='LOF' 表示 LOF 基金
    lof_funds = pro.fund_basic(market='E', fund_type='LOF')
    return lof_funds


# 获取 LOF 基金的市场价格和净值
def get_lof_data(ts_code, start_date, end_date):
    try:
        # 获取市场价格
        market_data = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        # 获取基金净值
        nav_data = pro.fund_nav(ts_code=ts_code, start_date=start_date, end_date=end_date)

        # 检查数据是否为空
        if market_data.empty or nav_data.empty:
            print(f"数据获取失败，请检查基金代码 {ts_code} 或日期范围。")
            return pd.DataFrame()

        # 合并数据
        data = pd.merge(market_data, nav_data, left_on='trade_date', right_on='nav_date')
        return data
    except Exception as e:
        print(f"数据获取失败，错误信息：{e}")
        return pd.DataFrame()


# 计算溢价/折价率
# 管理费、托管费已计入基金净值
def calculate_premium_discount(data):
    data['premium_rate'] = (data['close'] - data['unit_nav']) / data['unit_nav'] * 100
    data['discount_rate'] = (data['unit_nav'] - data['close']) / data['unit_nav'] * 100
    #     print("溢价/折价率计算结果：")
    #     print(data[['trade_date', 'close', 'unit_nav', 'premium_rate', 'discount_rate']])
    return data


# 计算波动率
def calculate_volatility(data, window=3):
    data['returns'] = data['close'].pct_change()  # 计算每日收益率
    #     print("收益率计算结果：")
    #     print(data[['trade_date','close','returns']])
    data['volatility'] = data['returns'].rolling(window=window, min_periods=1).std() * np.sqrt(252)  # 年化波动率
    #     print("波动率计算结果：")
    #     print(data[['trade_date', 'close', 'volatility']])
    return data


# 监控 LOF 套利机会
def monitor_lof_arbitrage(ts_code, start_date, end_date, volatility_window=3):
    data = get_lof_data(ts_code, start_date, end_date)
    if data.empty:
        print("无有效数据，无法计算套利机会。")
        return

    data = calculate_premium_discount(data)
    data = calculate_volatility(data, window=volatility_window)

    # 计算溢价套利机会
    data['premium_arbitrage'] = data['premium_rate'] > (data['volatility'] + cost)
    premium_opportunities = data[data['premium_arbitrage']]
    if not premium_opportunities.empty:
        print(f"LOF {ts_code} 存在溢价套利机会：")
        print(premium_opportunities[['trade_date', 'close', 'unit_nav', 'premium_rate', 'volatility']])
    else:
        print(f"LOF {ts_code} 无溢价套利机会。")

    # 计算折价套利机会
    data['discount_arbitrage'] = data['discount_rate'] > (data['volatility'] + cost)
    discount_opportunities = data[data['discount_arbitrage']]
    if not discount_opportunities.empty:
        print(f"LOF {ts_code} 存在折价套利机会：")
        print(discount_opportunities[['trade_date', 'close', 'unit_nav', 'discount_rate', 'volatility']])
    else:
        print(f"LOF {ts_code} 无折价套利机会。")


#     return data

lof_funds = get_lof_funds()

lof_list = lof_funds[pd.to_datetime(lof_funds['list_date']) < start_date]

# 选择前十种 LOF 基金进行监控
for _, row in lof_list[:10].iterrows():
    ts_code = row['ts_code']
    print(row['name'])
    monitor_lof_arbitrage(ts_code, start_date=start_date, end_date=end_date)