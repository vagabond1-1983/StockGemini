import ollama
import time
import base64


# 将图像转换为 base64 编码
with open(r'/resources/demo-top20.png', "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
messages = [
    {
        "role": "user",
        "content": "排除名称后R或者红点的干扰，识别出每一行的代码、名称和封单额，请确保代码、名称、封单额是一一对应的，如果有一行中的某一个字段识别有问题，请忽略整行，最终只需要输出代码、名称和封单额",
        "image": encoded_image
    }
]
#记录下请求开始时间
start_time = time.time()
resp = ollama.chat(model='qwen3-vl:8b', messages=messages)
# 记录下请求结束时间
end_time = time.time()
print(f"请求耗时: {end_time - start_time}秒")
print(resp)