import requests
import base64
import time

def image_recognition_with_ollama(image_path):
    """
    使用 ollama 服务对图像进行识别
    """
    # 将图像转换为 base64 编码
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    # 构造请求体
    payload = {
        "model": "qwen3-vl:8b",
        "prompt": "排除名称后R或者红点的干扰，识别出每一行的代码、名称和封单额，请确保代码、名称、封单额是一一对应的，如果有一行中的某一个字段识别有问题，请忽略整行，最终只需要输出代码、名称和封单额",
        "images": [encoded_image],
        "stream": False,
        "max_tokens": 5000
    }

    #记录下请求开始时间
    start_time = time.time()
    # 发送请求到 ollama 服务
    response = requests.post("http://127.0.0.1:11434/api/generate", json=payload)

    # 记录下请求结束时间
    end_time = time.time()
    print(f"请求耗时: {end_time - start_time}秒")

    if response.status_code == 200:
        result = response.json()
        return result.get("response", "")
    else:
        raise Exception(f"API调用失败: {response.text}")

# 示例调用
# result = image_recognition_with_ollama(r'D:\Resources\python\StockDataParser\resources\demo.png')
result = image_recognition_with_ollama(r'/resources/demo-top20.png')
print(result)
