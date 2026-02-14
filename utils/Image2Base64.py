import subprocess

import win32clipboard
from io import BytesIO
from PIL import Image
import base64
import os
import time
import config.GlobalConfig as config
from utils.SSHConnection import SSHConnection

DELAY_SECONDS = 5

logger = config.jingjia_logger('AutoJingJia')

def get_image_from_clipboard():
    """
    将剪切板的内容作为图像解析为base64二进制码
    :return:
    """
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            # 处理 DIB 格式数据
            image = Image.open(BytesIO(data))
            buffer = BytesIO()
            image.save(buffer, format='png')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    finally:
        win32clipboard.CloseClipboard()

def take_tdx_screenshot(snip_area, save_path=None):
    """
    使用Snipaste进行指定区域截图，保存到文件中
    """
    # 读取截图内容并编码为base64的二进制内容
    for _ in range(5):
        if os.path.exists(save_path):
            with open(save_path, 'rb') as f:
                png_data = f.read()
                return base64.b64encode(png_data).decode('utf-8')
        else:
            command = f'{config.SNIPASTE_PATH} snip --delay {DELAY_SECONDS} --{snip_area} -o "{save_path}"'
            logger.debug(f"执行截图命令：{command}")
            subprocess.run(command, shell=True, check=True, timeout=30)
            logger.debug(f"截图已保存到文件：{save_path}")

            time.sleep(3)
    raise Exception("截图文件不存在")


def take_remote_tdx_screenshot(remote_client):
    """
    登录远程机器进行tdx的截图，将截图文件放到共享文件夹，读取后转为base64编码
    :param snip_area:
    :param save_path:
    :return:
    """
    for _ in range(5):
        # 登录远程机器，执行截图命令
        file_name = f'{time.strftime("%Y%m%d-%H%M%S")}_tdx_screenshot.png'
        screenshot_cmd = f'{config.MAC_SCREENSHOT_CMD}'.replace("{file_name}", file_name)
        logger.info(f"将要在{config.MAC_IP}机器上执行的命令为：{screenshot_cmd}")
        output, error = remote_client.remote_start_process(screenshot_cmd)

        shared_file_path = os.path.join(config.MAC_SHARE_PATH, file_name)
        for _ in range(3):
            time.sleep(2)
            if os.path.exists(shared_file_path):
                # 读取截图文件并转为base64编码
                with open(shared_file_path, 'rb') as f:
                    png_data = f.read()
                    return base64.b64encode(png_data).decode('utf-8')
        logger.warning(f"截图出现问题，重新尝试。输出：{output},{error}")

if __name__ == '__main__':
    client = SSHConnection(config.MAC_IP, config.MAC_USER, config.MAC_PASSWORD)
    client.echo()
    print(take_remote_tdx_screenshot(client))