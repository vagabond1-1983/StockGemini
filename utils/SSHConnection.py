import os.path
import time

import paramiko
import config.GlobalConfig as config

logger = config.jingjia_logger('AutoJingJia')

class SSHConnection:
    def __init__(self, hostname, username, password):
        try:
            # 创建SSH客户端
            client = paramiko.SSHClient()
            # 自动添加主机密钥
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 连接到远程主机
            client.connect(hostname=hostname, username=username, password=password)
            self.client = client
        except Exception as e:
            logger.error(f"SSH连接失败: {str(e)}")
            raise e

    def close(self):
        self.client.close()

    def echo(self):
        self.remote_start_process("echo hello")

    @staticmethod
    def safe_decode(byte_data, encodings=['utf-8', 'gbk', 'latin-1']):
        if byte_data is None:
            return None
        """安全解码字节数据"""
        for encoding in encodings:
            try:
                return byte_data.decode(encoding)
            except UnicodeDecodeError:
                continue
        # 如果所有编码都失败，使用错误替换
        return byte_data.decode('utf-8', errors='replace')

    def remote_start_process(self, command):
        """
        远程启动进程
        :param hostname: 目标主机IP
        :param username: 登录用户名
        :param password: 登录密码
        :param command: 要执行的命令（如启动程序的命令）
        """
        error = None
        try:
            # 执行命令
            stdin, stdout, stderr = self.client.exec_command(command)
            # 获取命令输出
            output_bytes = stdout.read()
            error_bytes = stderr.read()

            output = SSHConnection.safe_decode(output_bytes)
            error = SSHConnection.safe_decode(error_bytes)

            logger.info(f"命令执行成功: {command}")
            logger.info(f"输出: {output}")
            if error:
                logger.error(f"错误: {error}")
            return output, error
        except Exception as e:
            logger.error(f"远程执行失败: {str(e)}")
            return None, str(e)
        finally:
            return None, error


# 使用示例
if __name__ == "__main__":
    # 笔记本截图，把图像保存在本地共享目录下，PC读取已经映射的网络驱动器中的截图文件
    filename=f"{time.strftime('%Y%m%d-%H%M%S')}.png"
    screenshot_path = fr"C:\share\{filename}"
    cmd = rf'cd /d c:\softwares\snipaste && Snipaste.exe snip --full -o "{screenshot_path}"'
    ssh = SSHConnection(
        hostname="192.168.1.3",  # 目标机器IP
        username="vagab",  # 用户名
        password="vagab",  # 密码
    )
    ssh.remote_start_process("echo hello")
    # ssh.remote_start_process(cmd)
    # print(os.path.exists(fr"Z:\{filename}"))
    ssh.close()

    # 启动Python脚本（Linux示例）
    # remote_start_process(
    #     hostname="192.168.1.101",
    #     username="user",
    #     password="password",
    #     command="nohup python3 /path/to/script.py > /dev/null 2>&1 &"
    # )