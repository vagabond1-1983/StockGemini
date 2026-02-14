import tushare as ts
import time
"""
开盘啦榜单数据接口文档：https://tushare.pro/document/2?doc_id=347
感谢光临，订单: 3176523015838294783，本单发货内容如下：

==================
接口地址请修改为:
http://tushare.top/dataapi
请求token是: 
8ieskv7fheqqpctiek
==================

【小提示】：
1、因非官网token，所以长度不一样是正常情况，本店承诺保证数据质量
2、如提示token无效，必定是激活代码没生效，请参考链接中的代码示例修改 https://tushare.top/docs
"""
pro = ts.pro_api()
pro._DataApi__token    = "8ieskv7fheqqpctiek" #⬅️你拿到token 以后替换
pro._DataApi__http_url = "http://tushare.top/dataapi" # 这里固定值，原封不动拷贝

# ========= daily 日线接口 ============
# df = pro.daily(trade_date='20180810',limit=20)
# print(df)
# # =========  交易日历 =========
# df_cal = pro.trade_cal(exchange='', start_date='20250101', end_date='20251231' ,limit=5, offset=0)
# print(df_cal)
# # ========= 5000积分验证 ======
# dfkpl_concept_cons = pro.kpl_concept_cons(trade_date='20241014')
# print(dfkpl_concept_cons)
# # ========= 10000积分验证 =======
# dflimit_list_ths = pro.limit_list_ths(trade_date='20241125', limit_type='涨停池', fields='ts_code,trade_date,tag,status,lu_desc')
# print(dflimit_list_ths)

df = pro.kpl_list(trade_date=time.strftime('%Y%m%d'), tag='涨停', fields='ts_code,name,trade_date,lu_time,last_time,limit_order,theme,status')
# dataframe数据按照表格方式将内容无省略打印出来
print(df.to_string())