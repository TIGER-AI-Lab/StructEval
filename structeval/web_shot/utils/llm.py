from aioconsole import aprint
from openai import AsyncOpenAI


async def async_openai(messages, retries=3):
    aclient = AsyncOpenAI(
        base_url="https://api.360.cn/v1",
        api_key="fk430334544.mHpI9XuMEtnHp5aSqrsS8QdQFcGcf2epd0287120"
    )
    # aclient = AsyncOpenAI(
    #     base_url="https://api.together.xyz/v1",
    #     api_key="c9055fb6d917265f28b8f132728125004dca8f48c173bf54f7383d6b23557f5d"
    # )
    # aclient = AsyncOpenAI(
    #     base_url="http://localhost:8000/v1",
    #     api_key="token-abc123"
    # )

    for attempt in range(retries):
        try:
            completion = await aclient.chat.completions.create(
                # model="gpt-4o",
                # model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                model="/home/azureuser/yifan/models/Llama-3.1-70B-Instruct",
                messages=messages
            )
            res = completion.choices[0].message.content
            break
        except Exception as e:
            await aprint(e, "Retrying...")
            if attempt == retries - 1:
                res = "ERROR"

    return res
