import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__)))

from utils.MarkFileHandler import MyConfigParser

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_PATH = BASE_PATH + '/resources'

import logging
from utils.logger_config import setup_logging, get_logger
from logging.handlers import TimedRotatingFileHandler


config = MyConfigParser(os.path.join(RESOURCES_PATH, '.env'), encoding='utf-8')

# --------------------global config --------------------
IS_DEBUG = config.read_option('global', 'DEBUG') == 'True'
SCREENSHOT_SAVE_DIR = config.read_option('global', 'SCREENSHOT_SAVE_DIR')
SNIPASTE_PATH = config.read_option('global', 'SNIPASTE_PATH')
TDX_MARK_FILE = config.read_option('global', 'TDX_MARK_FILE')
TDX_MARK_BAK_FILE = config.read_option('global', 'TDX_MARK_BAK_FILE')
ZT_ANALYSIS_PATH = config.read_option('global', 'ZT_ANALYSIS_PATH')
DAILY_ZT_PATH = config.read_option('global', 'DAILY_ZT_PATH')
# ---------------------end of global config --------------------

# ---------------------tdx config --------------------
SCREENSHOT_AREA = config.read_option('tdx_snap', 'SCREENSHOT_AREA')
# ---------------------end of tdx config --------------------

# ---------------------mac config --------------------
MAC_IP = config.read_option('mac', 'MAC_IP')
MAC_USER = config.read_option('mac', 'MAC_USER')
MAC_PASSWORD = config.read_option('mac', 'MAC_PASSWORD')
MAC_SCREENSHOT_CMD = config.read_option('mac', 'MAC_SCREENSHOT_CMD')
MAC_SHARE_PATH = config.read_option('mac', 'MAC_SHARE_PATH')
# ---------------------end of mac config --------------------

# ---------------------jiuyan config --------------------
JY_LOGIN_URL = config.read_option('jiuyan', 'JY_LOGIN_URL')
JY_ACTION_URL = config.read_option('jiuyan', 'JY_ACTION_URL')
JY_PHONE = config.read_option('jiuyan', 'JY_PHONE')
JY_PASSWORD = config.read_option('jiuyan', 'JY_PASSWORD')
# ---------------------end of jiuyan config --------------------

# ---------------------qwen config --------------------
DASHSCOPE_API_KEY = config.read_option("qwen", "DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = config.read_option("qwen", "DASHSCOPE_BASE_URL")
QWEN_IMAGE_MODEL = config.read_option("qwen", "IMAGE_MODEL")
# ---------------------end of qwen config --------------------

# ---------------------gemini config --------------------
CHATAI_API_KEY = config.read_option("gemini", "CHATAI_API_KEY")
CHATAI_GEMINI_BASE_URL = config.read_option("gemini", "CHATAI_BASE_URL")
# ---------------------end of gemini config --------------------


_logger_instance = None
def jingjia_logger(logger_name):
    global _logger_instance
    if _logger_instance is None:
        setup_logging()
        _logger_instance = get_logger(logger_name)
        # 配置特定的文件处理器
        # file_handler = logging.FileHandler(filename=RESOURCES_PATH + '/JingJia.log', encoding='utf-8')
        # file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        # logger.addHandler(file_handler)
        if IS_DEBUG:
            _logger_instance.setLevel(logging.DEBUG)
        # 创建时间处理器，默认保留7天，默认每10秒执行一次
        time_handler = TimedRotatingFileHandler(filename=os.path.join(RESOURCES_PATH, f'JingJia-{time.strftime('%Y-%m-%d', time.localtime())}.log'), when='midnight', interval=7,
                                                backupCount=10, encoding='utf-8')
        time_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        if IS_DEBUG:
            time_handler.setLevel(logging.DEBUG)
        _logger_instance.addHandler(time_handler)
    return _logger_instance

def read_option(section, option):
    return config.read_option(section, option)