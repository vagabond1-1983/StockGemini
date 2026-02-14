import logging
import logging.config
import os


def setup_logging():
    """使用配置文件设置日志"""
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(BASE_PATH, 'logging.conf')

    logging.config.fileConfig(config_path)


def get_logger(name):
    """获取日志记录器"""
    return logging.getLogger(name)
