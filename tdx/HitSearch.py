"""
    概念查找
    输入：4位code
    输出：1. TIPWORD 2. TIP
    过程：
    1. 根据尾号在mark查出code
    2. 根据code查询出股票名称
    3. 显示code的TIPWORD即备注
    4. 显示code的TIP即涨停原因

    TODO 输入关键词，反向找到相关股票列表，展示：名称、代码和概念
    输入：关键词 -p
    输出：列表，展示：名称、代码和概念
    过程：
    1. 根据输入的结尾标识，判断是进行关键词查找
    2. 在TIP中查找关键词，支持正则表达式？，将找到的code列表暂存
    3. 根据code查询股票名称和TIPWORD，收集到一个df中
    4. 打印出这个df，方便用户根据code继续查询单个概念
"""

import re
import os
import sys
import logging
import pandas as pd
import time

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.MarkFileHandler import MyConfigParser
from mootdx.quotes import Quotes
from mootdx.server import bestip

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_PATH = BASE_PATH + '/resources'

# 从resources下的.env文件中读取配置
config = MyConfigParser(RESOURCES_PATH + '/.env', encoding='utf-8')
TDX_MARK_FILE = config.get('global', 'tdx_mark_file')

# 读取mark.dat文件供多处使用
mark_reader = MyConfigParser(TDX_MARK_FILE, encoding='gbk')

CODE_MODE = 1
KEYWORD_MODE = 2

logger = None
client = None

def __init():
    global logger, client
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(RESOURCES_PATH + '/hit_search.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger(__name__)

    # 初始化连接tdx
    bestip(console=True)
    client = Quotes.factory(market='std', bestip=True)

def input_verify_code():
    _user_input_code = input("请输入股票代码（4位或者6位），或者输入关键词（以-p结尾）进行查找)：")
    if len(_user_input_code) == 4 or len(_user_input_code) == 6:
        return _user_input_code, CODE_MODE
    elif _user_input_code.endswith(' -p'):
        return _user_input_code.replace(' -p', ''), KEYWORD_MODE
    else:
        logger.error("输入的股票代码格式有误，请重新输入")
        return input_verify_code()


def get_code_by_tail_number(_user_input_code):
    stocks = mark_reader.read_section('MARK')
    for stock in stocks:
        if str(stock).endswith(_user_input_code):
            return stock, True
    return _user_input_code, False


def get_stock_name_by_code(stock_code):
    # 连接tdx并查询出股票的名称
    company_brief_info = client.F10(symbol=stock_code)['公司概况']
    pattern = fr'{stock_code}\s+([\u4e00-\u9fa5]+) 更新日期'
    company_name = re.search(pattern, company_brief_info)
    if company_name:
        return company_name.group(1)
    else:
        return 'unknown'


def get_codes_by_keyword(user_input):
    """
    根据用户输入的关键词查询出股票代码，关键词支持正则
    :param user_input: 关键词，中文、英文、数字、正则
    :return: 代码列表
    """
    tip_dict = mark_reader.read_section('TIP')
    # 循环tip字典，找出匹配上关键词的股票代码
    return [key for key, value in tip_dict.items() if re.search(user_input, value, re.I)]


if __name__ == '__main__':
    __init()
    logger.info("启动概念查询程序^--^")

    # 等待用户输入并检查格式
    user_input,  mode = input_verify_code()
    if mode == CODE_MODE:
        logger.info(f'用户输入的股票代码为：{user_input}')
    elif mode == KEYWORD_MODE:
        logger.info(f'用户输入的关键词为：{user_input}')

    # 开始概念查询过程
    # 根据股票代码查询出单个股票概念
    if mode == CODE_MODE:
        #1.根据尾号在mark查出code，并标识是否存在
        market_code, is_exist = get_code_by_tail_number(user_input)
        code = market_code[2:]
        if is_exist:
            #2.根据code查询出股票名称
            stock_name = get_stock_name_by_code(code)
            logger.info(f'股票名称为：{stock_name}，code为：{code}')

            #3.存在则显示code的TIPWORD即备注
            stock_tipword = mark_reader.get('TIPWORD', market_code)
            logger.info(f'股票的概念为：{stock_tipword}')
            #4.存在则显示code的TIP即涨停原因
            stock_tip = mark_reader.get('TIP', market_code)
            logger.info(f'股票的涨停原因为：{stock_tip}')
        else:
            logger.info(f'该股票没有记录在mark.dat中，请在同花顺中查找必要信息：{code}')
    # 根据关键词查询出多个股票列表
    elif mode == KEYWORD_MODE:
        stock_codes = get_codes_by_keyword(user_input)
        # 如果列表为空，则提示用户没有查询到相关概念
        if len(stock_codes) == 0:
            logger.info(f'没有找到与{user_input}相关的概念')
        else:
            logger.info(f'找到的代码列表为：{stock_codes}')
            result_df = pd.DataFrame(columns=['名称', '代码', '概念'])
            for stock_code in stock_codes:
                real_stock_code = stock_code[2:]
                # 根据code查询出股票名称
                try:
                    stock_name = get_stock_name_by_code(real_stock_code)
                except Exception as e:
                    stock_name = '无名称'
                    logger.error(f'查询股票{real_stock_code}名称时出错：{e}')
                # 根据code查询备注
                try:
                    stock_tipword = mark_reader.get('TIPWORD', stock_code)
                except Exception as e:
                    stock_tipword = '无备注'
                # 将名称、代码、备注添加到df中
                result_df.loc[len(result_df)] = [stock_name, real_stock_code, stock_tipword]
            logger.info(result_df)