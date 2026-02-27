"""
竞价阶段超预期情况解读：
1. 925竞价加封
2. 930竞价抢筹
---
2026.1.13 实现了925竞价加封的事件播报，还在想法完善和代码调优过程中
2026.1.17 在925竞价结束后，利用gemini对昨天封单额和今天封单额进行对比分析，并给出分析结果指向做多或者做空，辅助情绪判定并提醒决策
2026.1.24 将加封事件放入队列，当有新的加封事件时，跟队列中相同加封金额对比，如果是以1.7倍数级增长则继续播报并提醒，如果加封幅度小于1.7倍则不进行提示
2026.1.26 将昨天和今天封单额对比改为今天920和今天925的封单额对比，打印出表格。目的是看真实抢筹时间，资金的态度和情绪
2026.2.14 修改封单额类型处理失败的bug
2026.2.19 收集并打印竞价分析期间所有处理过的df
"""
import os
import re
import shutil
import time
import sys

from utils.SSHConnection import SSHConnection

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


import utils.Image2Base64 as ima
import utils.TextParser as parser
import utils.VoiceNotice as vn
from utils.MarkFileHandler import MyConfigParser
import pandas as pd
import config.GlobalConfig as config

BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESOURCES_PATH = BASE_PATH + '/resources'

logger = config.jingjia_logger('AutoJingJia')


ZHANGTING_PROMPT = """
       排除名称后R或者红点的干扰，识别出每一行的序号、代码、名称、封单额和开盘%，请确保代码、名称、封单额是一一对应的，如果有一行中的某一个字段识别有问题，请忽略整行，最终只需要输出序号、代码、名称、封单额和开盘%
       返回数据格式以csv方式输出，表头为：序号, 代码, 名称, 封单额、开盘%，且仅输出csv格式数据，不输出分析过程
       """
# 涨停封单额加封阈值1亿
ZTAMOUT_THRESHOLD = 1

# 创建当天日期的文件夹
today_folder = RESOURCES_PATH + '/' + time.strftime('%Y-%m-%d', time.localtime())
if not os.path.exists(today_folder):
    os.makedirs(today_folder)

# 封单额记录文件
ZT_925_AMOUNT_PATH = os.path.join(RESOURCES_PATH, '925_zt_amounts')
ZT_925_TODAY_FILE = os.path.join(ZT_925_AMOUNT_PATH, 'TODAY.csv')
ZT_925_YESTERDAY_FILE = os.path.join(ZT_925_AMOUNT_PATH, 'YESTERDAY.csv')
ZT_920_TODAY_FILE = os.path.join(ZT_925_AMOUNT_PATH, '920.csv')

remote_client = None

def detect_zt_amount():
    """
    竞价阶段920后进行一次指定位置截图，获取到相应股票的代码、名称、封单额信息，方便后续对加封事件的判定
    :return:
    """
    global remote_client
    # 1. 开始截图
    logger.debug(f"开始截图")
    screenshot_path = today_folder + '/' + time.strftime('%H%M%S', time.localtime()) + '.png'
    image_data = ima.take_tdx_screenshot(config.SCREENSHOT_AREA, screenshot_path)
    # image_data = ima.take_remote_tdx_screenshot(remote_client)
    # 2. 图像识别出当前截图的股票数据
    logger.debug(f"开始截图的识别工作")
    df = parser.image_recognition_with_dashscope(image_data, ZHANGTING_PROMPT)
    logger.debug(f"识别完成")
    return df

def is_collect_jj_end(origin_min):
    """
    集合竞价是否结束，即时间晚于925
    :return:
    """
    if config.IS_DEBUG:
        return time.localtime().tm_min > origin_min + 1
    else:
        # 通过时间比较函数，判断当前时间晚于9:25:30秒
        jj_end_tt = pd.Timestamp(f"{time.strftime('%Y-%m-%d', time.localtime())} 9:25:30")
        return pd.Timestamp.now() > jj_end_tt

def opt_ztscreen_df(zt_df):
    """
    对截图生成的df进行优化处理：
    1. 将封单额形如：1亿，5000万，转换为以亿为单位的数值
    :param zt_df:
    :return:
    """
    if zt_df is None:
        return None
    opt_df = pd.DataFrame(columns=zt_df.columns)
    opt_df['封单额'] = opt_df['封单额'].astype(float)
    for index, row in zt_df.iterrows():
        # 如果封单额单位不是万或者亿，说明没有封单，则从df中去除
        unit = row['封单额'][-1]
        value = row['封单额'][:-1]
        try:
            if unit == '万':
                value = float(value) / 10000
            elif unit == '亿':
                value = float(value)
            else:
                value = 0
            row['封单额'] = str(value)
        except Exception as e:
            logger.error(f"{row['名称']}的封单额格式错误：{row['封单额']}，跳过优化处理不进行后续操作")
        opt_df = pd.concat([opt_df, row.to_frame().T], ignore_index=True)
    opt_df['封单额'] = opt_df['封单额'].astype(float)
    return opt_df

def compare_zt_record(yesterday_df, curr_df):
    """
    对比当天股票封单额和上次记录下的股票封单额，记录下当天封单额大于1亿的股票，形成df
    :param yesterday_df:
    :param curr_df:
    :return:
    """
    compared_df = pd.DataFrame(columns=['代码', '名称', '当天封单额', '上次封单额', '差值', '开盘%', '概念'])
    for index, row in curr_df.iterrows():
        if row['代码'] in yesterday_df['代码'].tolist():
            # 获取昨日封单额
            yesterday_amount = yesterday_df[yesterday_df['代码'] == row['代码']]['封单额'].values[0]
            # 获取当前封单额
            curr_amount = row['封单额']
            if curr_amount >= 1:
                # 计算差值
                diff_amount = float(curr_amount) - float(yesterday_amount)
                # 添加到结果中
                new_row = pd.DataFrame({'代码': [row['代码']], '名称': [row['名称']],
                                        '当天封单额': [row['封单额']], '上次封单额': [yesterday_amount],
                                        '差值': [diff_amount], '开盘%': [row['开盘%']],
                                        '概念': [row.get('概念', '--')]})
                if not new_row.empty:
                    compared_df = pd.concat([compared_df, new_row.dropna(how='all')], ignore_index=True, sort=False)
    # 将差值设置的更醒目
    compared_df['差值'] = compared_df['差值'].apply(lambda x: f"\033[91m{x:.2f}\033[0m" if x > 1 or x < -1 else f"{x:.2f}")
    return compared_df


def read_zt_record(zt_file_path):
    # 用today.csv的内容覆盖yesterday.csv，如果yesterday.csv不存在，则创建一个空的yesterday.csv
    if not os.path.exists(zt_file_path):
        return None
    # 读取文件内容
    return pd.read_csv(zt_file_path, encoding='utf-8', dtype={'代码': str, '封单额': float})

def add_topic_on_head(zt_df):
    mark_reader = MyConfigParser(config.TDX_MARK_BAK_FILE, encoding='gbk')
    result_df = zt_df.copy()
    result_df['概念'] = '--'
    concepts = []

    for _, row in zt_df.iterrows():
        # 将代码转换为通达信格式代码，上证前缀01，深证前缀00
        tdxcode = '01' + row['代码'] if re.match(r'^6[08]', row['代码']) else '00' + row['代码']
        topic = mark_reader.read_option('TIPWORD', tdxcode)
        concept = re.sub(r'^[1-9]', '', topic) if topic is not None else '--'
        concepts.append(concept)

    result_df['概念'] = concepts
    return result_df

def increase_amount_detect():
    """
    920开始进行一次基准封单额的数据采集；等待20秒后再次进行数据采集和比对，目的是找出加封事件。如果有则语音播报出来，没有则进入下一次循环，直到925退出循环
    :return:
    """
    # 如果today.csv存在，则将内容覆盖yesterday.csv
    if not config.IS_DEBUG:
        if os.path.exists(ZT_925_TODAY_FILE):
            if os.path.exists(ZT_925_YESTERDAY_FILE):
                os.remove(ZT_925_YESTERDAY_FILE)
            shutil.move(ZT_925_TODAY_FILE, ZT_925_YESTERDAY_FILE)

    # 初始化远程mac
    # global remote_client
    # try:
    #     remote_client = SSHConnection(config.MAC_IP, config.MAC_USER, config.MAC_PASSWORD)
    #     remote_client.echo()
    # except Exception as e:
    #     logger.error(f"初始化远程mac失败: {str(e)}，无法进行检测，考虑备用方案TODO")
    #     return None

    # 920截图的第一次基准数据
    logger.info("进行基准数据的采集")
    pack_all_attacks_df = pd.DataFrame(columns=['时间', '单次df'])
    origin_df = detect_zt_amount()
    origin_df = opt_ztscreen_df(origin_df)

    # 920的基准数据缓存，方便后面的数据比对
    origin_df = add_topic_on_head(origin_df)
    origin_df = origin_df[origin_df['封单额'] >= 1]
    if not config.IS_DEBUG:
        origin_df.to_csv(ZT_920_TODAY_FILE, index=False, header=True, encoding='utf-8')
    pack_all_attacks_df = pd.concat([pack_all_attacks_df, pd.DataFrame({'时间': [time.strftime('%H:%M:%S', time.localtime())],
                                                                            '单次df': [origin_df]})], ignore_index=True)

    origin_min = time.localtime().tm_min

    # 判断是否到了9:25，如果时间到停止；如果没有到则继续进行一次截图，并将本次结果和基准数据进行比对，找出是否有加封的股票事件
    while True:
        if is_collect_jj_end(origin_min):
            logger.info(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}，集合竞价结束")

            # 进行920封单额和925封单额的对比，将对比结果输出为一个df
            logger.info("读入920封单额情况")
            today920_df = read_zt_record(ZT_920_TODAY_FILE)
            if today920_df is not None:
                compared_df = compare_zt_record(today920_df, curr_df)
                # 以表格形式输出对比结果到logger
                logger.info(f"920vs925对比\n{compared_df.to_string(index=False)}")
                vn.voice_notice('封单情况对比已经打印完毕，请查看控制台')
            # 将最新结果写入到封单额记录文件中
            logger.info("写入今天封单额情况")
            # 过滤掉封单额小于1的行
            curr_df = curr_df[curr_df['封单额'] >= 1]
            curr_df = add_topic_on_head(curr_df)
            pack_all_attacks_df = pd.concat([pack_all_attacks_df, pd.DataFrame({'时间': [time.strftime('%H:%M:%S', time.localtime())],
                                                                                    '单次df': [curr_df]})], ignore_index=True)
            if not config.IS_DEBUG:
                curr_df.to_csv(ZT_925_TODAY_FILE, index=False, header=True, encoding='utf-8')
            break
        else:
            logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}开始一次采集")
            curr_df = detect_zt_amount()
            curr_df = opt_ztscreen_df(curr_df)

            # 检查origin_df中相同代码的封单额大小，如果相差大于1亿，则放入一个新的df中
            if origin_df is None or curr_df is None:
                logger.error("本次数据采集失败，数据为空不满足检查条件，继续进入下一次采集")
                continue
            pack_all_attacks_df = pd.concat([pack_all_attacks_df, pd.DataFrame({'时间': [time.strftime('%H:%M:%S', time.localtime())],
                                                                               '单次df': [curr_df]})], ignore_index=True)
            logger.info("检查是否有加封事件")
            increased_df = parser.zhangting_increase(origin_df, curr_df, ZTAMOUT_THRESHOLD)
            if len(increased_df) > 0:
                logger.info(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}，有加封事件")
                # 将df中的结果包装为一段文本，给出关键信息：名称、当前封单额及差值
                notice_text = '<prosody pitch="high">请注意有加封事件!</prosody>'
                for index, row in increased_df.iterrows():
                    notice_text += f"<prosody rate='slow'>{row['名称']}，加封：{row['差值']}，当前封单额：{row['封单额']}</prosody><break time='500ms'>"
                logger.info(notice_text)

                vn.voice_notice(notice_text[:500])
            else:
                logger.info(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}，无加封事件")
    if today920_df is None:
        # 925提示看情绪风标表现，判定市场情绪
        vn.voice_notice('<prosody pitch="high">时间：925，选票前请先看情绪风标表现，判定市场情绪</prosody>')
    else:
        # 利用AI比较昨天和今天的封单情况，从专业角度判定今天的市场是做多还是做空，以便在开盘前更好的判定市场情绪适不适合出手
        emo_prompt = f"""
请作为股票专家，基于下面给出的昨天和今天的集合竞价封单额数据进行对比，完成以下任务：
1. 对比两天的整体封单情况：统计1亿以上封单的家数（分别统计涨停封单和跌停封单中1亿以上的家数）、计算1亿以上封单的总封单额（分别统计涨停和跌停方向的总封单额），分析封单额大小变化，判断资金态度是做多还是做空，形成明确的做多/做空信号结论；同时结合涨停封单对应的概念及封单金额，分析资金主要的做多方向。要求先给出结论（需包含做多/做空信号及资金做多方向），再用表格方式简洁呈现对比分析（表格需包含对比维度：1亿以上涨停封单家数、1亿以上涨停封单总金额、1亿以上跌停封单家数、1亿以上跌停封单总金额，以及昨天、今天的具体数据和变化情况）。
2. 基于上述得出的做多/做空信号结论及资金做多方向，撰写30秒的盘前内参风格口播稿，以“各位投资者”开头，采用结论先行的方式，语言口语化、简洁明了，突出核心判断、关键数据变化及资金做多方向，无需提及表格内容。
说明：数据中封单额列的单位是亿元；开盘%列如果是正数则是涨停封单，如果是负数则是跌停封单
---昨天封单数据---
{today920_df.to_string()}
---今天封单数据---
{curr_df.to_string()}
        """
        start_time = time.time()
        resp = parser.gemini_chat(emo_prompt)
        end_time = time.time()
        logger.debug(f"提示词打印：{emo_prompt}\n分析结果为：{resp}\n耗时：{end_time - start_time:.2f}秒")
        # 将结果进行语音播报
        result_announcement = f'<prosody pitch="high">{resp[resp.find("各位投资者")+6:]}</prosody>'
        logger.info(f"语音播报内容：{result_announcement}")
        vn.voice_notice(result_announcement)
    # TODO 打印本次所有处理过的df信息，未来考虑用大模型做整体分析和方向预判
    logger.info("打印本次所有处理过的df信息")
    logger.info(pack_all_attacks_df.to_string())


def notice_before_attack():
    notice_text = f'<prosody pitch="high">{config.NOTICE_BEFORE_ATTACK}</prosody>'
    vn.voice_notice(notice_text)


if __name__ == '__main__':
    logger.info("读入920封单额情况")
    today920_df = read_zt_record(ZT_920_TODAY_FILE)
    curr_df = read_zt_record(ZT_925_TODAY_FILE)
    if today920_df is not None:
        compared_df = compare_zt_record(today920_df, curr_df)
        # 以表格形式输出对比结果到logger
        logger.info(f"920vs925对比\n{compared_df.to_string(index=False)}")
