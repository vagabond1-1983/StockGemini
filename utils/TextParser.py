from openai import OpenAI
import time
import pandas as pd
from io import StringIO
from google import genai
from google.genai import types

import config.GlobalConfig as config

logger = config.jingjia_logger('AutoJingJia')

# 创建一个千问client
def qwen_client():
    return OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
        # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
        api_key=config.DASHSCOPE_API_KEY,
        # 以下是北京地域base-url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
        base_url=config.DASHSCOPE_BASE_URL,
    )

# 创建一个gemini client
def gemini_client():
    return OpenAI(
        api_key=config.CHATAI_API_KEY,
        base_url=config.CHATAI_GEMINI_BASE_URL,
    )

def image_recognition_with_dashscope(png_data, prompt):
    # 构造图像输入
    image_data = f"data:image/png;base64,{png_data}"
    try:
        # 记录下请求开始时间
        start_time = time.time()
        completion = qwen_client().chat.completions.create(
            # model="qwen3-vl-flash",
            model=config.QWEN_IMAGE_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": image_data,
                            # 输入图像的最小像素阈值，小于该值图像会放大，直到总像素大于min_pixels
                            # "min_pixels": 32 * 32 * 3,
                            # 输入图像的最大像素阈值，超过该值图像会缩小，直到总像素低于max_pixels
                            # "max_pixels": 32 * 32 * 8192
                        },
                        # 模型支持在以下text字段中传入Prompt，若未传入，则会使用默认的Prompt：Please output only the text content from the image without any additional descriptions or formatting.
                        {"type": "text",
                         "text": prompt}
                    ]
                }
            ])
        content = completion.choices[0].message.content
        # 记录下请求结束时间
        end_time = time.time()
        logger.info(f"请求耗时: {end_time - start_time}秒")

        # 将csv格式的content结果转换为dataFrame形式
        df = pd.read_csv(StringIO(content), dtype={'代码': str})
        # print(f"原始数据：{df}")
        # 去除表头的单引号及空格
        df.columns = df.columns.str.replace(' ', '').str.replace(r'^[\'"]|[\'"]$', '', regex=True)
        # 去除所有字段中的空格，代码那一列的值保留
        columns_to_process = [col for col in df.columns if col != '代码']
        df[columns_to_process] = df[columns_to_process].apply(lambda x: x.astype(str).str.replace(' ', '', regex=True))
        return df
    except Exception as e:
        logger.error(f"错误信息: {e}")


# 加封事件缓存,key-代码，value-增加的封单额
increase_amount_cache = {}
def need_alert(code, origin_amount, new_amount, threshold):
    """
    通过原封单额及新封单额和阈值比较，如果原封单额为0说明是新加封，返回差值和是否计入加封事件
    :param origin_amount:
    :param new_amount: 
    :param threshold: 
    :return: 
    """
    origin_amount = float(origin_amount)
    new_amount = float(new_amount)
    distance = new_amount - origin_amount
    is_increase = False
    # 1. 判断原封单额是否为0，如果是0，则判断是否符合计入加封事件的条件：即新封单额大于0.3亿
    if origin_amount == 0:
        if new_amount > 0.3:
            is_increase = True
    # 2. 如果原封单额大于0，则判断差值是否大于阈值，且差值为原值的1/5以上，则认为有加封事件
    else:
        if (new_amount - origin_amount) > threshold and (new_amount - origin_amount) > origin_amount / 5:
            is_increase = True

    # 对于增加封单，接着判断此封单额是否超出预期（增长是否达到70%以上），如果是则需要触发提示，如果不是则不触发提示。再把触发提示的增长额记录缓存中，用于下次判断依据
    pect = 1.7
    if is_increase:
        # 判断增长数值小于之前记录的70%，判定为未超出预期，不需要触发提示
        if code in increase_amount_cache and distance < increase_amount_cache[code] * pect:
            logger.info(f"{code}的增长为：{distance}未超出记录值：{increase_amount_cache[code]}的{pect}倍，不触发提示")
            is_increase = False
        else:
            # 缓存增加封单额
            increase_amount_cache[code] = distance
    return distance, is_increase

def zhangting_increase(origin_df, df, threshold):
    """
    检查origin_df中相同代码的封单额大小，如果相差大于xx亿，则放入一个新的df中
    :param origin_df: 原始数据
    :param df: 最新数据
    :return: 相差大于给定阈值的数据行
    """
    # 构建一个空的dataFrame，用于存储结果，表头跟origin_df一致
    new_columns = origin_df.columns
    new_df = pd.DataFrame(columns=new_columns)
    for index, row in df.iterrows():
        try:
            # 获取当前封单额
            curr_amount = row['封单额']
            # 检查origin_df中是否有此代码，有则检查是否有加封事件；没有则判断封单额是否大于3000万
            if row['代码'] in origin_df['代码'].values:
                origin_row = origin_df[origin_df['代码'] == row['代码']]
                # print(f'开始比较数据项：{origin_row}')
                # 如果len是1，说明920的原始数据也有此记录，则进行封单额的比较；
                if len(origin_row) == 1:
                    origin_row = origin_row.iloc[0]
                    # 如果封单额最后一位是万，则将封单额除以10000
                    origin_amount = origin_row['封单额']
                    logger.debug(f"{origin_row['名称']}的原始封单额：{origin_amount}，最新封单额：{curr_amount}")
                    # 差值大于阈值且差值为原值的1/5以上，则认为有加封事件
                    distance, is_increase = need_alert(row['代码'], origin_amount, curr_amount, threshold)
                    if is_increase:
                        # 将封单额增加值写入到新字段差值中
                        row['差值'] = f"{distance:.2f}亿"
                        logger.info(f"{origin_row['名称']}的封单额增加：{row['差值']}")
                        # 将当前行加入新的dataFrame中
                        new_df = pd.concat([new_df, row.to_frame().T], ignore_index=True)
            else:
                distance, is_increase = need_alert(row['代码'], 0, curr_amount, threshold)
                if is_increase:
                    # 将封单额增加值写入到新字段差值中
                    row['差值'] = f"{distance:.2f}亿"
                    logger.info(f"{row['名称']}的封单额增加：{row['差值']}")
                    new_df = pd.concat([new_df, row.to_frame().T], ignore_index=True)
        except Exception as e:
            logger.error(f"{row}处理失败，错误信息: {e}")
    return new_df

def chat_model(model_name, prompt, extra_body=None):
    completion = qwen_client().chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{prompt}"},
        ],
        extra_body=extra_body,
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
    print("AI: ", end="", flush=True)

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
    print(f"\n--- 完整回复 ---\n{full_response}")

# gemini模型
def gemini_chat(prompt):
    client = genai.Client(
        api_key = config.CHATAI_API_KEY,
        vertexai=True,  # 可选，优先使用vertexai协议访问，稳定性更高
        http_options={
            "base_url": config.CHATAI_GEMINI_BASE_URL
        },
    )

    model_name_key = 'GEMINI_MODEL'
    if config.IS_DEBUG:
        model_name_key = 'GEMINI_MODEL_DEBUG'

    model_name = config.read_option('gemini', model_name_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig()
    )
    return response.text


if __name__ == '__main__':
    prompt = """
    请作为股票专家，基于下面给出的2026.1.9和2026.1.12的集合竞价封单额数据进行对比，回答下面的两个问题，一个问题一个问题回答，并分段。
1. 对比两天的整体封单情况：1亿以上封单的家数和封单额大小变化，12号对比9号的竞价结果，资金态度是做多还是做空，先给出结论再用表格方式简洁进行简洁分析
2. 严格筛选出“特别超出预期”的股票。
“特别超出预期”的定义（必须同时满足以下任一条件）：
突增型：该股在前一日封单额为零或极低（例如<5亿），而在当日封单额大幅跃升至高位（例如>10亿或进入当日TOP 5）。
跃升型：该股在前一日未上榜或排名靠后（例如>第15名），而在当日排名大幅提升至前列（例如进入当日TOP 5）。
排除项：
封单额和排名均保持稳定或仅小幅波动的股票（即使金额巨大）。
封单额或排名显著下滑的股票。
封单额小于3亿以下
输出要求：
仅列出符合上述“特别超出预期”标准的股票。
输出格式为表格，包含列：股票代码、股票名称、上一次封单额、最新封单额。
---
2026.1.9
代码,名称,封单额
002931,锋龙股份,44.8
600783,鲁信创投,23.6
600477,杭萧钢构,21.5
002342,巨力索具,8.67
000987,越秀资本,6.76
601106,中国一重,2.54
002431,棕榈股份,2.37
603017,中衡设计,2.25
600869,远东股份,1.74
603938,三孚股份,1.04
---
2026.1.12
序号,代码,名称,封单额
1,002131,利欧股份,38.6
2,002931,锋龙股份,37.1
3,002044,美年健康,20.3
4,603598,引力传媒,16.8
5,600477,杭萧钢构,16.4
6,002792,通宇通讯,13.5
7,600776,东方通信,12.2
8,000681,视觉中国,8.95
9,600783,鲁信创投,7.44
10,603000,人民网,5.59
11,002774,快意电梯,5.31
12,002969,嘉美包装,4.41
13,003007,直真科技,3.17
14,603496,恒为科技,3.11
15,002342,巨力索具,3.01
16,300986,志特新材,2.84
17,600676,交运股份,1.92
18,603305,旭升集团,1.43
19,600880,博瑞传播,1.35
20,600637,东方明珠,1.31
    """
    start_time = time.time()
    result = chat_model("qwen3-max-preview", prompt, extra_body={"enable_thinking": True})
    print(result)
    end_time = time.time()
    print(f"总耗时：{end_time - start_time}秒")