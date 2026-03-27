"""
    读取resources下指定json文件，解析出文件中涨停的股票及原因，方便导入到excel中做后续处理
    下一步可能直接写入到通达信的mark文件，直接做标记，省去手动标记烦恼
    1. 导入指定json
    2. 解析出action filed输出此涨停板块的主题
    3. 接着解析出每个板块下article的code，name，edition，expound
    4. 获取通达信数据：涨停股票的连板天数，韭研下是几天几板，不是连板天数，因此修正下
    5. 读取之前在mark.dat文件下已经备注过的股票概念，方便一致性
    6. 导出为同名的csv文件
    ---
    下面是需要手动调整的
    1. 打开csv文件，复制到当月涨停分析文档中
    2. 调整通达信涨停股备注

    ---20250921 改版
    1. 通过requests登录韭研并获取指定日期的涨停数据
    2. 去掉生成json和csv中间文件的过程
    3. 通过命令行完成脚本执行，脚本为ps1在桌面
    4. TODO excel中如果存在相同的sheet则会报错，希望用替换sheet页方式避免报错

    ---20251001 改版
    1. TIP内容加上板块信息，方便快速识别出炒作的概念
    2. excel中用替换sheet页方式避免报错

    ---20251012
    1. 当有备注概念但是跟指定日期的概念有不同时，往往是增加或者修改了上涨概念，需要对备注进行更新

    ---20251213
    1. 去除将指定日期涨停列表导入到excel中
    2. 新增将指定日期首板票按照概念分类写入txt中，方便进行同花顺导入，输出txt的路径

    ---20251231
    1. 只截取custom_mark的前7个字符，避免封单额的数字被遮住
"""
import json
import os
import sys
import logging
import time
# from importlib.metadata import pass_none

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jsonpath
import pandas as pd
import shutil
from GetUpDays4tdx import TdxQuotes
from utils.MarkFileHandler import MyConfigParser
import requests
from datetime import datetime
import re
import config.GlobalConfig as config

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_PATH = os.path.join(BASE_PATH, 'resources')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(RESOURCES_PATH, 'stock_action_parser.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# 从resources下的.env文件中读取配置
tdx = TdxQuotes()

DAILY_ZT_PATH = os.path.join(RESOURCES_PATH, config.DAILY_ZT_PATH)

# 读取mark备份文件供多处使用
mark_reader = MyConfigParser(config.TDX_MARK_BAK_FILE, encoding='gbk')

# 生成当前的timestamp毫秒级
timestamp = str(int(time.time() * 1000))
logger.info(f"当前时间戳为：{timestamp}")
JIUYAN_DEFAULT_HEADER = {
    'Content-Type': 'application/json',
    'Timestamp': timestamp,
    'Platform': '3',
    'Token': '1111'
}

def fetch_data_from_api(url, payload=None, headers=None):
    """
    发送HTTP POST请求并获取JSON响应

    Args:
        url (str): 请求的URL
        payload (dict, optional): POST请求的数据
        headers (dict, optional): 请求头信息

    Returns:
        dict: JSON响应数据
    """
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()  # 如果响应状态码不是200会抛出异常
        json_data = response.json()
        logger.info(f"成功获取API数据: {url}")
        return json_data
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP请求失败: {url}, 错误: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"响应不是有效的JSON格式: {e}")
        raise
    except Exception as e:
        logger.error(f"获取API数据时发生未知错误: {e}")
        raise

def load_stock_data(stock_req_dict):
    headers = JIUYAN_DEFAULT_HEADER
    headers['Cookie'] = f"SESSION={stock_req_dict['session_id']}"
    payload = {
        "date": stock_req_dict['date'],
        "pc": 1
    }
    zt_json = fetch_data_from_api(config.JY_ACTION_URL, payload, headers)
    try:
        review_date = jsonpath.jsonpath(zt_json, '$.data[0].date')[0]
        if str(review_date) != str(stock_req_dict['date']):
            logger.error(f"API返回的日期与请求的日期不一致: {review_date} != {stock_req_dict['date']}")
            raise ValueError("API返回的日期与请求的日期不一致")
        return  zt_json.get('data')
    except Exception as e:
        logger.error(f"解析API数据时发生错误: {e}")
        logger.error(f"获取到的原始结果为：{zt_json}")
        raise


def update_question_mark(current_reason, origin_tip, exist_mark, update_mark):
    # 如果exist_mark不存在，说明是未收录过的涨停，则tip不提示？
    if exist_mark is None:
        return update_mark

    # 将之前标注过的首位涨停板数去掉
    pure_exist_mark = exist_mark[1:] if len(exist_mark) > 1 else exist_mark
    # 获取现在涨停原因概念，从current_reason首字母开始截取到\t作为涨停原因概念
    current_tip_reason = current_reason[:current_reason.find('\t')]

    # 获取之前记录的涨停原因概念，从origin_tip的#$**开始，截取到\t作为涨停原因概念
    origin_tip_reason = current_tip_reason
    if origin_tip is not None:
        origin_tip_reason = origin_tip[origin_tip.find('#$**') + 4 : origin_tip.rfind('\t')]

    # 根据之前的涨停原因和当前涨停原因的比较，更新备注信息的待更新标记
    if origin_tip_reason == '' and pure_exist_mark[0] != '?':
        update_mark = "?" + pure_exist_mark
    # 判断涨停原因是否相同
    elif origin_tip_reason == current_tip_reason:
        update_mark = pure_exist_mark[1:] if pure_exist_mark[0] == '?' else pure_exist_mark
    else:
        # 涨停原因不同且exist_mark首位不为?且概念不是其他或者公告，则加上 ?
        if pure_exist_mark[0] != '?' and (current_tip_reason != '其他' and current_tip_reason != '公告'):
            update_mark = "?" + pure_exist_mark
    return update_mark

def expend_data(field, field_reason, stock=None):
    stock_info = {}
    #  股票代码
    code = jsonpath.jsonpath(stock, '$..code')[0]
    tdx_code = '01' + code[2:] if code.startswith('sh') else '00' + code[2:]
    stock_info['code'] = tdx_code

    # 股票名称
    name = jsonpath.jsonpath(stock, '$..name')[0]
    stock_info['name'] = name

    # 股票涨停概念板块
    stock_info['field'] = field

    # 涨停时间
    time = jsonpath.jsonpath(stock, '$..time')[0]
    if time is None or time == '':
        logger.warning(f"{code}-{name}无涨停时间，跳过")
        return None
    stock_info['time'] = time

    # 涨停天数，这里的edition是几天几板跟连板是不同的，需手动再修改下
    # edition = jsonpath.jsonpath(stock, '$..edition')[0]
    # zt_day = 1 if edition is None else edition
    # stock_info['edition'] = zt_day
    zt_day = tdx.get_up_days(code[2:])
    stock_info['edition'] = zt_day

    # 涨停原因，分为简略和详细解析
    field_tab_reason = f'{field}\t{field_reason}'
    expound = jsonpath.jsonpath(stock, '$..expound')[0]
    simple_reason = expound.split('\n')[0]
    stock_info['simple_reason'] = simple_reason
    stock_info['TIP'] = str(expound).replace('\n', '\t') + f'#$**{field_tab_reason}**'

    exist_mark = mark_reader.read_option('TIPWORD', stock_info['code'])
    # 默认设置mark为韭研的涨停原因简要的
    mark = stock_info['simple_reason'][:14]
    # 2025.10.12 ~~如果exist_mark不为None，且跟mark不同，则在exist_mark前加上问号表示需要更新；~~
    # 2025.11.8 当且仅当涨停原因和TIP里的涨停原因不同时，才在exist_mark前加上问号表示需要更新
    mark = update_question_mark(field_tab_reason, mark_reader.read_option('TIP', stock_info['code']), exist_mark, mark)

    # 备注，去除以 '+' 结尾的情况
    stock_info['custom_mark'] = mark[:-1] if mark.endswith('+') else mark

    # 导入tdx的列
    # 1. MARK
    stock_info['MARK'] =  "7"
    # 2. 备注颜色
    match stock_info['edition']:
        # 值为0代表当天没有涨停，作为备注股票涨停原因的补偿方式
        case 0:
            stock_info['TIPCOLOR'] = "0xffffff"
        # 首板蓝色
        case 1:
            stock_info['TIPCOLOR'] = "16048642"
        # 2板绿色
        case 2:
            stock_info['TIPCOLOR'] = "65280"
        # 3板以上红色
        case _:
            stock_info['TIPCOLOR'] = "255"
    # 3. TIPWORD
    # 2025.12.31 只截取custom_mark的前7个字符，避免封单额的数字被遮住
    short_mark =  stock_info['custom_mark'][:7]
    if stock_info['edition'] == 0:
        stock_info['TIPWORD'] = short_mark
    else:
        stock_info['TIPWORD'] = f"{stock_info['edition']}{short_mark}"

    logger.debug(f"成功处理股票数据: {code}-{name}")
    return stock_info

# 解析json文件，提取板块及个股涨停信息，结构化为df包含个股编码、名称、连涨天、涨停原因及通达信mark.dat写入字段
def analysis_jyzt_export_df(stock_req_dict):
    json_data = load_stock_data(stock_req_dict)
    awesome_stock_df = pd.DataFrame(columns=['code', 'name', 'edition', 'time', 'simple_reason', 'TIP', 'custom_mark', 'MARK', 'TIPCOLOR', 'TIPWORD', 'field'])

    # 遍历json_data下的数组
    for item in json_data:
        children = item.get('count')
        field = item['name']
        field_reason = item['reason']
        if children > 0 and field != 'ST板块':
            logger.info(f"开始处理{field}板块")
            # 先写入板块信息，把code字段作为板块名，name字段作为板块上涨原因
            awesome_stock_df = pd.concat([awesome_stock_df, pd.DataFrame([{'code': field, 'name': field_reason.replace('\n', '')}])], ignore_index=True)

            field_stocks = item['list']
            # 遍历每个板块中的上榜股票
            for stock in field_stocks:
                stock_info = expend_data(field, field_reason, stock)

                if stock_info is not None:
                    awesome_stock_df = pd.concat([awesome_stock_df, pd.DataFrame([stock_info])], ignore_index=True)
            logger.info(f"{field}板块处理完成")
    return awesome_stock_df


def write2mark(stock_infos_df, sections):
    try:
        mark_writer = MyConfigParser(config.TDX_MARK_FILE, encoding='gbk')
        for section in sections:
            # 先将当天涨停个股的信息增量写入
            for index, row in stock_infos_df.iterrows():
                # 当前section的行数据为空则跳过，因为是板块行
                try:
                    if not pd.isna(row[section]):
                        mark_writer.increment_write(section, row['code'], row[section])
                except Exception as e:
                    logger.warning(f"{row['code']}写入失败，原因：{e}")
        # 再将原先记录的个股信息修改：TIPWORD的涨停天数去掉，COLOR修改下颜色区别当天涨停
        # if section == 'TIPWORD':
        #     tipwords = mark_reader.read_section(section)
        #     for code, tipword in tipwords.items():
        #         # 判断code是否不存在于stock_infos_df中，不存在则将tipword的涨停天数去掉
        #         if code not in stock_infos_df['code'].values:
        #             mark_writer.increment_write(section, code, tipword[1:])
        # 只把非当天涨停的标的颜色改为白色，避免和当天涨停的标冲突。不改变备注内容和涨停天数
            if section == 'TIPCOLOR':
                colors = mark_reader.read_section(section)
                for code, color in colors.items():
                    # 判断code不存在于stock_infos_df中或者存在但是edition是0，则将color换成白色
                    if code not in stock_infos_df['code'].values or stock_infos_df.loc[stock_infos_df['code'] == code, 'edition'].values[0] == 0:
                        mark_writer.increment_write(section, code, '16777215')
        mark_writer.save()
        logger.info("mark.dat文件写入完成")
    except Exception as e:
        logger.error(f"写入mark.dat文件时出错: {e}")
        raise


def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"{file_path}文件删除成功")
    else:
        logger.warning(f"{file_path}文件不存在")


def login_jiuyan():
    login_url = config.JY_LOGIN_URL
    payload = {
        "phone": config.JY_PHONE,
        "password": config.JY_PASSWORD
    }
    try:
        user_info = fetch_data_from_api(login_url, payload, JIUYAN_DEFAULT_HEADER)
        session_token = jsonpath.jsonpath(user_info, '$.data.sessionToken')[0]
        logger.info(f"登录成功，session_token: {session_token}")
        return session_token
    except  Exception as e:
        logger.error(f"登录失败: {e}，请求结果打印：{user_info}")
        raise


def input_date():
    # 提示用户输入日期并获取
    _action_date = input("请输入日期(格式为yyyy-mm-dd): ")
    # 如果action_date为空，则使用当前日期；如果action_date的格式为yyyyMMdd，则修改格式为yyyy-mm-dd
    if not _action_date:
        _action_date = datetime.now().strftime("%Y-%m-%d")
    elif len(_action_date) == 8:
        _action_date = datetime.strptime(_action_date, "%Y%m%d").strftime("%Y-%m-%d")
    else:
        # 判断格式是否为yyyy-mm-dd，否则提示用户输入错误并退出
        if not re.match(r"\d{4}-\d{2}-\d{2}", _action_date):
            logger.error(f"输入的日期格式不对，请重新输入！")
            sys.exit(1)
    logger.info(f"复盘日期为：{_action_date}")
    return _action_date

# 将stock_infos_df中首板的票过滤出来并以概念分类，写入到一个txt文件中
def write_first_edition_2_txt(stock_infos_df, action_date):
    # 把df中edition为1的首板票，按照field概念分类，写入一个新的dataFrame中
    first_edition_df = stock_infos_df[stock_infos_df['edition'] == 1]
    # 修改df中code字段，把前两位去除
    first_edition_df.loc[:, 'code'] = first_edition_df['code'].str.slice(2)
    # 按field分类，先按time升序排序，然后聚合code并通过逗号连接，同时计算count
    first_edition_df = first_edition_df.sort_values(by=['field', 'time'], ascending=[True, True])
    first_edition_grouped = first_edition_df.groupby('field').agg({
        'code': lambda x: ','.join(x)
    }).reset_index()

    # 添加count字段统计每个field中code的个数
    field_counts = first_edition_df.groupby('field')['code'].count().reset_index()
    field_counts.columns = ['field', 'count']

    # 合并结果
    result_df = first_edition_grouped.merge(field_counts, on='field')
    # 按照count从大到小重新排序result_df，并将filed='公告'和'其他'的概念排在最后
    result_df = result_df.sort_values(by=['count'], ascending=False)
    result_topic_df = result_df[(result_df['field'] != '公告') & (result_df['field'] != '其他')]
    result_general_df = result_df[(result_df['field'] == '公告') | (result_df['field'] == '其他')]
    result_final_df = pd.concat([result_topic_df, result_general_df], ignore_index=True)
    # 将first_edition_df输出到一个txt文件中
    FIRST_EDITION_TXT_FILE = os.path.join(DAILY_ZT_PATH, f"{action_date}.txt")
    try:
        with open(FIRST_EDITION_TXT_FILE, 'w', encoding='utf-8') as f:
            for index, row in result_final_df.iterrows():
                f.write(f"{row['field']}\t{row['code']}\n")
                # 计算出code中有多少个逗号，没有逗号记为1
            total_count = result_final_df['count'].sum()
            f.write(f"共{total_count}只涨停股")
        logger.info(f"{FIRST_EDITION_TXT_FILE}文件生成完成")
    except Exception as e:
        logger.error(f"{FIRST_EDITION_TXT_FILE}文件生成失败: {e}")


    


if __name__ == '__main__':
    logger.info("开始今天的涨停复盘^--^")

    session_id = login_jiuyan()

    # 备份原始文件
    shutil.copyfile(config.TDX_MARK_FILE, config.TDX_MARK_BAK_FILE)
    logger.info(f"{config.TDX_MARK_FILE}文件备份完成")

    # 获取涨停复盘日期
    action_date = input_date()

    # 解析韭研json，形成股票涨停信息及mark所需字段的列表
    stock_req_dict = {"session_id": session_id, "date": action_date}
    stock_infos_df = analysis_jyzt_export_df(stock_req_dict)
    # print(f"csv文件生成完成")

    # 分别增量写入mark.dat文件
    logger.info("开始写入mark.dat文件")
    write2mark(stock_infos_df, ['MARK', 'TIPCOLOR', 'TIPWORD', 'TIP'])
    logger.info("写入mark.dat文件完成。\n下面是需要手动调整的内容：\n1. 调整通达信涨停股备注\n2. 调整同花顺备注\n3. 调整同花顺板块个股顺序")

    # 将stock_infos_df中首板的票过滤出来并以概念分类，写入到一个txt文件中
    write_first_edition_2_txt(stock_infos_df,action_date)

    '''
    # 如果ZT_ANALYSIS_PATH文件不存在，则新建一个文件
    if  not os.path.exists(ZT_ANALYSIS_PATH):
        workbook = openpyxl.Workbook()
        workbook.save(ZT_ANALYSIS_PATH)
        workbook.close()
    # 将stock infos内容汇总到当月涨停分析excel中，方便查找
    with pd.ExcelWriter(ZT_ANALYSIS_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        stock_infos_df.to_excel(writer, index=False, sheet_name=action_date)
    logger.info(f'【{action_date}】sheet页添加完成到{ZT_ANALYSIS_PATH}中')
    '''
    logger.info("涨停复盘结束**************************************")
