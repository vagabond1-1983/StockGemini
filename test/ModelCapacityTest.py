import time
import os

from openai import OpenAI
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from anthropic import Anthropic

# https://platform.closeai-asia.com/pricing
CLOSEAI_API_KEY = 'sk-Ne4NGGO9TdzBbB84X0oBBFXP8hVB2nHyYHxx3ETsaDKH4p7h'
# https://console.cloud.google.com/vertex-ai/studio?hl=zh-cn&project=gen-lang-client-0086864153
GEMINI_KEY = 'AQ.Ab8RN6LERvnTj9KR7ftffaxviiSj94M8Ul5xR2jUykZG4hGxnQ'

def openai_test(base_url, model, prompt):
    client = OpenAI(
        base_url= base_url,
        api_key = CLOSEAI_API_KEY,
    )
    response = client.chat.completions.create(
        model= model,
        messages=[
            {"role": "system", "content": "你是一个股票专家"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    return response

def gemini_test(base_url, model, prompt):
    if base_url is not None:
        client = genai.Client(
            api_key = CLOSEAI_API_KEY,
            vertexai=True,  # 可选，优先使用vertexai协议访问，稳定性更高
            http_options={
                "base_url": base_url
            },
        )
    else:
        http_options = types.HttpOptions(
            headers={
                'http_proxy': 'socks5:127.0.0.1:10808'
            }
        )
        client = genai.Client(
            api_key = GEMINI_KEY,
            vertexai=True,
            # http_options=http_options,
        )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig()
    )
    return response

def anthropic_test(base_url, model, prompt):
    client = Anthropic(
        api_key = CLOSEAI_API_KEY,
        base_url=base_url,
    )

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.7,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ]
    )
    return message

def qwen_thinking_test(base_url, model, prompt):
    client = OpenAI(
        base_url=base_url,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    completion = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model=model,
        messages=[
            {"role": "system", "content": "你是一个股票专家"},
            {"role": "user", "content": f"{prompt}"},
        ],
        extra_body={"enable_thinking": True},
        # 流式输出方式调用
        stream=True,
        # 使流式返回的最后一个数据包包含Token消耗信息
        stream_options={
            "include_usage": True
        }
    )

    # 处理流式响应
    # 用列表暂存响应片段，最后 join 比逐次 += 字符串更高效
    content_parts = []

    for chunk in completion:
        if chunk.choices:
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
            content_parts.append(content)
        elif chunk.usage:
            print("\n--- 请求用量 ---")
            print(f"输入 Tokens: {chunk.usage.prompt_tokens}")
            print(f"输出 Tokens: {chunk.usage.completion_tokens}")
            print(f"总计 Tokens: {chunk.usage.total_tokens}")

    full_response = "".join(content_parts)
    return full_response

def get_response_text(response, api_type):
    """
    统一获取响应文本内容
    """
    if api_type == "openai":
        return response.choices[0].message.content
    elif api_type == "gemini":
        return response.text
    elif api_type == "anthropic":
        return response.content
    else:
        raise ValueError(f"不支持的 API 类型: {api_type}")

if __name__ == '__main__':
    prompt = """
请作为股票专家，基于下面给出的昨天和今天的集合竞价封单额数据进行对比，完成以下任务：
1. 对比两天的整体封单情况：统计1亿以上封单的家数（分别统计涨停封单和跌停封单中1亿以上的家数）、计算1亿以上封单的总封单额（分别统计涨停和跌停方向的总封单额），分析封单额大小变化，判断资金态度是做多还是做空，形成明确的做多/做空信号结论；同时结合涨停封单对应的概念及封单金额，分析资金主要的做多方向。要求先给出结论（需包含做多/做空信号及资金做多方向），再用表格方式简洁呈现对比分析（表格需包含对比维度：1亿以上涨停封单家数、1亿以上涨停封单总金额、1亿以上跌停封单家数、1亿以上跌停封单总金额，以及昨天、今天的具体数据和变化情况）。
2. 基于上述得出的做多/做空信号结论及资金做多方向，撰写30秒的盘前内参风格口播稿，以“各位投资者”开头，采用结论先行的方式，语言口语化、简洁明了，突出核心判断、关键数据变化及资金做多方向，无需提及表格内容。
说明：数据中封单额列的单位是亿元；开盘%列如果是正数则是涨停封单，如果是负数则是跌停封单
---昨天封单数据---
序号      代码    名称    封单额    开盘%      概念
0   1  002931  锋龙股份  23.60  10.00     优必选
1   2  603078   江化微  19.80  10.02     光刻胶
2   3  000670   盈方微  19.40  10.00   分销+研发
3   4  000880  潍柴重机  11.10  10.00  发电机+船舶
4   5  002279  久其软件   9.70  10.05    AI营销
5   6  002165   红宝丽   4.97   9.98     光刻胶
6   7  301023  奕帆传动   3.45  20.00      --
7  11  603778  国恩科技  17.70 -10.01     钙钛矿
8  12  002131  利欧股份  79.90 -10.00    AI营销
---今天封单数据---
序号      代码    名称   封单额     开盘%       概念
0    1  000066  中国长城  23.4    9.99  业绩减亏+国产
1    2  002931  锋龙股份  22.4   10.01      优必选
2    3  000670   盈方微  18.1   10.05    ?销+研发
3    4  603078   江化微  16.2    9.99  上海国资入主+
4    5  002636  金安国纪  11.9   10.01      PCB
5    6  000880  潍柴重机   2.6    9.99   ?电机+船舶
9   10  603778  国晟科技  15.0  -10.02      钙钛矿
10  11  002131  利欧股份  90.4  -10.04     AI营销
            """
    # openai
    # start_time = time.localtime()
    # openai_resp =  openai_test('https://api.openai-proxy.org/v1', 'gpt-5.2', prompt)
    # end_time = time.localtime()
    # print(f"openai response:\n{get_response_text(openai_resp, 'openai')}")
    # openai_resp_time = time.mktime(end_time) - time.mktime(start_time)
    # print(f"openai response time: {openai_resp_time}s")

    # gemini
    start_time = time.localtime()
    # gemini_resp = gemini_test('https://api.openai-proxy.org/google', 'gemini-3-flash-preview', prompt)
    # gemini_resp = gemini_test('https://api.openai-proxy.org/google', 'gemini-3-pro-preview', prompt)
    gemini_resp = gemini_test(None, 'gemini-3-pro-preview', prompt)
    end_time = time.localtime()
    print(f"gemini response:\n{get_response_text(gemini_resp, 'gemini')}")
    gemini_resp_time = time.mktime(end_time) - time.mktime(start_time)
    print(f"gemini response time: {gemini_resp_time}s")

    # anthropic
    # start_time = time.localtime()
    # anth_resp = anthropic_test('https://api.openai-proxy.org/anthropic', 'claude-sonnet-4-5', prompt)
    # end_time = time.localtime()
    # print(f"anthropic response:\n{get_response_text(anth_resp, 'anthropic')}")
    # resp_time = time.mktime(end_time) - time.mktime(start_time)
    # print(f"anthropic response time: {resp_time}s")

    # deepseek
    # start_time = time.localtime()
    # ds_resp = openai_test('https://api.openai-proxy.org/v1', 'deepseek-chat', prompt)
    # end_time = time.localtime()
    # print(f"deepseek response:\n{get_response_text(ds_resp, 'openai')}")
    # ds_resp_time = time.mktime(end_time) - time.mktime(start_time)
    # print(f"deepseek response time: {ds_resp_time}s")

    # 模型结果比较
    # compare_prompt = f"""
    #     根据问题和两个模型输出结果，评价两个模型输出结果之间的差异。要求从一个股票交易员评估市场热度的角度评价输出结果的专业性、客观程度及指导性，并将评价结果用一个0-10的分数表示，从三个维度分别打分再给出一个最终结论和总分。
    #     问题：{prompt}
    #     模型1输出结果：{get_response_text(openai_resp, 'openai')}，响应时间：{openai_resp_time}s
    #     模型2输出结果：{get_response_text(gemini_resp, 'gemini')}，响应时间：{gemini_resp_time}s
    # """
    # qwen_resp = qwen_thinking_test('https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen3-max-preview', compare_prompt)
    # print(f"qwen response:\n{qwen_resp}")