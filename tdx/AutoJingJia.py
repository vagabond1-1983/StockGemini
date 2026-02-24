"""
竞价截图：
2025.10.25 已实现：
1. 从9:15开始进行自动截图，分别对指定区域进行：915右侧半屏、920左侧右半、925左侧右半、925右侧半屏
2026.1.2
用千问大模型对920之后的tdx竞价也没进行解读，形成一个封单表格，当检测到加封5000万以上的个股进行加封事件语音播报
TODO
1. 对触发加封事件的个股，通过pywinauto方式加入到自选股中，方便快速定位和凹槽买入
2. 对923-925时段的竞价抢筹进行监控，当检测到抢筹非常激烈（需要定义）时，进行语音播报及添加到养鱼池中
"""
import os
import subprocess
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from pynput.keyboard import Key, Controller
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))
import config.GlobalConfig as config

import jingjia.ExceptionNoticeAfter920 as enotice

# 配置截图保存路径
DELAY_SECONDS = 5

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)
RESOURCES_PATH = BASE_PATH + '/resources'

logger = config.jingjia_logger('AutoJingJia')
# 创建键盘控制器
keyword = Controller()

def take_screenshot(topic, snip_area):
    """
    使用Snipaste进行指定区域截图，并以时间戳格式保存文件。
    """
    filename = f"{datetime.now().strftime('%Y%m%d')}_{topic}.png"
    filepath = os.path.join(config.SCREENSHOT_SAVE_DIR, filename)

    # 构建Snipaste命令行
    # 如果你的Snipaste已加入系统PATH，命令是 `Snipaste.exe`
    # 如果未加入，请使用完整路径，例如：r`C:\Program Files\Snipaste\Snipaste.exe`
    command = f'{config.SNIPASTE_PATH} snip --delay {DELAY_SECONDS} --{snip_area} -o "{filepath}"'

    try:
        # 执行命令
        subprocess.run(command, shell=True, check=True, timeout=30)
        logger.debug(f"cmd: {command}")
        logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 截图已保存: {filepath}")
    except subprocess.CalledProcessError:
        logger.error(f"[{datetime.now().strftime('%H:%M:%S')}] 错误：截图命令执行失败。")
    except subprocess.TimeoutExpired:
        logger.error(f"[{datetime.now().strftime('%H:%M:%S')}] 错误：截图操作超时。")
    except FileNotFoundError:
        logger.error(f"[{datetime.now().strftime('%H:%M:%S')}] 错误：未找到Snipaste程序，请检查其是否已安装并正确配置路径。")


def take_screenshot_n_times(topic, snip_area, times):
    """
    使用Snipaste进行指定区域的多次截图，并以时间戳格式保存文件。
    """
    for i in range(times):
        take_screenshot(f'{topic}-{i+1}', snip_area)
        # 等待30秒
        time.sleep(30)


def launch_tdx_program(tdx_path):
    """
    启动指定路径的TDX程序。打开程序后，1.回车登录，2.esc关闭广告弹窗，3.60进入沪深个股列表
    """
    try:
        subprocess.Popen(tdx_path)
        time.sleep(3)
        keyword.press(Key.enter)
        # time.sleep(5)
        # keyword.press(Key.esc)
        # time.sleep(2)
        # keyword.press('6')
        # keyword.press('0')
        # time.sleep(1)
        # keyword.press(Key.enter)
        # time.sleep(5)
    except Exception as e:
        logger.error(f"启动{tdx_path}程序时发生错误：{e}")

def launch_stock_programs(launch_code):
    match launch_code:
        case 0:
            # 启动同花顺2
            subprocess.Popen(r'D:\同花顺软件\同花顺副本\hexin.exe')
            time.sleep(5)
            # 启动雷电模拟器
            # subprocess.Popen(r'D:\programs\leidian\LDPlayer9\dnplayer.exe')
            # time.sleep(5)
            # 启动东方财富
            # subprocess.Popen(r'D:\programs\eastmoney\mainhigh.exe')
            # 启动通达信
            launch_tdx_program(r'D:\softwares\tdx\tdxw.exe')
            # 启动副屏通达信
            # launch_tdx_program(r'D:\programs\通达信专业研究版V7.66\TdxW(MPV 6.3.5 7.66).exe')

        case 1:
            # 启动通达信
            subprocess.Popen(r'D:\softwares\tdx\tdxw.exe')
        case 2:
            print("不打开股票程序")
    logger.info("股票程序已启动")
    # 启动OBS
    # subprocess.Popen(r'D:\Program Files\obs-studio\bin\64bit\obs64.exe')


def stop_record_of_obs():
    keyword.press(Key.shift)
    keyword.press('s')
    keyword.release(Key.shift)


def main():
    """
    主函数，设置定时任务并启动调度器。
    """
    # 确保保存目录存在
    os.makedirs(config.SCREENSHOT_SAVE_DIR, exist_ok=True)

    # 启动股票程序
    launch_code = input("请输入启动代码，回车-全部，1-只有通达信，2-不打开股票程序")
    if not launch_code:
        launch_code = 0
    else:
        launch_code = int(launch_code)
    launch_stock_programs(launch_code)

    # 创建调度器
    scheduler = BlockingScheduler()

    # 添加定时任务
    start_hour = 9
    start_minute = 15
    start_second = 15
    step = 5
    up_points = 'area 5 5 2530 1380'
    down_points = 'area 10 -1436 2560 1380'
    if config.ENABLE_SCREENSHOT_920:
        # 9:15:10截图一次，范围是下屏
        scheduler.add_job(take_screenshot_n_times, 'cron', hour=start_hour, minute=start_minute, second=start_second,
                          args=[f'{start_hour}{start_minute}封单额截图', up_points, 2])
        # 9:20截图一次，范围是下屏
        second_minute = start_minute + step
        scheduler.add_job(take_screenshot_n_times, 'cron', hour=start_hour, minute=second_minute, second=start_second,
                          args=[f'{start_hour}{second_minute}封单额截图', up_points, 10])
        # 9:25截图封单额及开盘金额，范围是下屏
        third_minute = second_minute + step
        scheduler.add_job(take_screenshot, 'cron', hour=start_hour, minute=third_minute, second=start_second,
                          args=[f'{start_hour}{third_minute}封单额及看盘金额截图', up_points])

        # 9:25截图柚子看盘，范围是上屏
        scheduler.add_job(take_screenshot, 'cron', hour=start_hour, minute=third_minute, second=start_second,
                          args=[f'{start_hour}{third_minute}柚子看盘截图', down_points])

        scheduler.add_job(enotice.notice_before_attack, 'cron', hour=start_hour, minute=third_minute, second=start_second)

        # 9:30截图柚子看盘，范围是上屏
        fourth_minute = third_minute + step
        scheduler.add_job(take_screenshot_n_times, 'cron', hour=start_hour, minute=fourth_minute, second=0,
                          args=[f'{start_hour}{fourth_minute}柚子看盘截图', down_points, 5])

        # 9:30截图局势分析，范围是下屏
        scheduler.add_job(take_screenshot_n_times, 'cron', hour=start_hour, minute=fourth_minute, second=0,
                          args=[f'{start_hour}{fourth_minute}局势分析截图', up_points, 5])

    # 9:20进行竞价加封事件的检测并提示
    if config.ENABLE_INCREASE_AMOUNT_DETECT:
        if config.IS_DEBUG:
            scheduler.add_job(enotice.increase_amount_detect, 'cron', hour=time.localtime().tm_hour, minute=time.localtime().tm_min, second=time.localtime().tm_sec + 1)
        else:
            scheduler.add_job(enotice.increase_amount_detect, 'cron', hour=start_hour, minute=second_minute - 1, second=start_second)

    # 9:45的任务为按下键盘的shift+s组合键
    # one_quarter_later = fourth_minute + 15
    # scheduler.add_job(lambda: keyword.press(Key.shift), 'cron', hour=start_hour, minute=one_quarter_later, second=0)
    # scheduler.add_job(lambda: keyword.press('s'), 'cron', hour=start_hour, minute=one_quarter_later, second=1)
    # scheduler.add_job(lambda: keyword.press('s'), 'cron', hour=start_hour, minute=one_quarter_later, second=2)
    # scheduler.add_job(lambda: keyword.press(Key.shift), 'cron', hour=start_hour, minute=one_quarter_later, second=3)

    print("竞价截图程序已启动... (按 Ctrl+C 退出)")

    try:
        scheduler.start()  # 启动调度器，程序将在此阻塞
    except (KeyboardInterrupt, SystemExit):
        print("\n定时截图程序已退出。")
    finally:
        # 清理程序在竞价阶段产生的截图等资源文件
        today_folder = RESOURCES_PATH + '/' + time.strftime('%Y-%m-%d', time.localtime())
        os.system(f"rm -rf {today_folder}")


if __name__ == "__main__":
    main()