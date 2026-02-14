from configparser import ConfigParser
import os

class MyConfigParser(ConfigParser):
    """
    1. 扩展ConfigParser类，支持增量写入配置项和配置值
    2. 允许读取重复的option，只保留最后出现的
    """

    def __init__(self, config_file=None, encoding='utf-8'):
        # 禁用插值功能，避免 '%' 字符导致的解析错误
        super().__init__(interpolation=None, strict=False)
        self.section_cache = {}
        self.config_file = config_file
        self.encoding = encoding
        if config_file and os.path.exists(config_file):
            self.read(config_file, encoding=encoding)
            self.section_cache = {}
            for section in self.sections():
                self.section_cache[section] = dict(self.items(section))

    def _read(self, fp, fpname):
        # 允许重复的 option，只保留最后出现的
        for line in fp:
            if line.strip().startswith('['):
                sectname = line.strip()[1:-1]
                if sectname not in self._sections:
                    self._sections[sectname] = self._dict()
                    self._current_section = sectname
                continue
            if self._current_section and '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                self._sections[self._current_section][key] = val
        return

    def read_section(self, section):
        """
        读取指定节下的所有配置项

        Args:
            section (str): 配置节名称

        Returns:
            dict: 配置项字典
        """
        return self.section_cache.get(section, {})

    def read_option(self, section, option):
        return self.section_cache.get(section, {}).get(option)

    def set_option(self, section, option, value=None):
        """
        增量设置配置项，如果节不存在则创建节

        Args:
            section (str): 配置节名称
            option (str): 配置项名称
            value (str, optional): 配置项值，默认为None
        """
        # 如果节不存在，则添加节
        if not self.has_section(section):
            self.add_section(section)

        # 设置配置项
        self.set(section, option, value)

    def add_section_if_not_exists(self, section):
        """
        如果节不存在则创建节

        Args:
            section (str): 配置节名称
        """
        if not self.has_section(section):
            self.add_section(section)

    def update_option(self, section, option, value):
        """
        更新配置项的值，如果节或配置项不存在则创建

        Args:
            section (str): 配置节名称
            option (str): 配置项名称
            value (str): 配置项值
        """
        self.add_section_if_not_exists(section)
        self.set(section, option, value)

    def save(self, config_file=None):
        """
        保存配置到文件

        Args:
            config_file (str, optional): 配置文件路径，如果未指定则使用初始化时的文件
        """
        file_path = config_file or self.config_file
        if not file_path:
            raise ValueError("未指定配置文件路径")

        # 当gbk编码时，写入文件时出现编码错误，使用errors='replace'忽略错误
        with open(file_path, 'w', encoding=self.encoding, errors='replace') as f:
            self.write(f)

    def increment_write(self, section, option, value, save_immediately=False):
        """
        增量写入配置项和值

        Args:
            section (str): 配置节名称
            option (str): 配置项名称
            value (str): 配置项值
            save_immediately (bool): 是否立即保存到文件，默认为True
        """
        self.update_option(section, option, value)
        if save_immediately and self.config_file:
            self.save()
