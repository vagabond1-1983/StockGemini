import os
import dashscope
import pyaudio
import time
import base64
import numpy as np

# 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

from utils.logger_config import get_logger
logger = get_logger('AutoJingJia')

def voice_notice(text, model="qwen3-tts-flash"):
    p = pyaudio.PyAudio()
    # 创建音频流
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=24000,
                    output=True)

    response = dashscope.MultiModalConversation.call(
        # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx"
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model=model,
        text=text,
        voice="Cherry",
        language_type="Chinese",  # 建议与文本语种一致，以获得正确的发音和自然的语调。
        stream=True
    )

    for chunk in response:
        if chunk.status_code != 200:
            raise Exception(chunk.status_code, chunk.message)
        if chunk.output is not None:
          audio = chunk.output.audio
          if audio.data is not None:
              wav_bytes = base64.b64decode(audio.data)
              audio_np = np.frombuffer(wav_bytes, dtype=np.int16)
              # 直接播放音频数据
              stream.write(audio_np.tobytes())
          if chunk.output.finish_reason == "stop":
              logger.error(f"finish at: {chunk.output.audio.expires_at}")
    time.sleep(0.8)
    # 清理资源
    stream.stop_stream()
    stream.close()
    p.terminate()