# src/agent_starter_python/api_client.py
import asyncio
import logging

class FxHumanApiClient:
    def __init__(self, token: str, session_id: str):
        self._token = token
        self._session_id = session_id
        logging.info(f"[API Client] FxHumanApiClient initialized for session {session_id}")

    async def send_task(self, text: str):
        """
        向你的后端 API 发送处理好的句子。
        这是一个异步操作，但不会阻塞主 Agent 流程。
        """
        # 在这里实现你的 API 调用逻辑
        # 例如，使用 aiohttp 或 httpx 库
        logging.info(f'[API Client] Sending task to API: "{text}"')
        
        # 模拟一个网络请求
        await asyncio.sleep(0.1) 
        
        # 实际实现中可能如下所示:
        # async with httpx.AsyncClient() as client:
        #     try:
        #         response = await client.post(
        #             "https://your-api-endpoint.com/task",
        #             json={"session_id": self._session_id, "text": text},
        #             headers={"Authorization": f"Bearer {self._token}"}
        #         )
        #         response.raise_for_status()
        #         logging.info(f"[API Client] Successfully sent task for text: '{text}'")
        #     except httpx.HTTPStatusError as e:
        #         logging.error(f"[API Client] HTTP error sending task: {e}")
        #     except Exception as e:
        #         logging.error(f"[API Client] An unexpected error occurred: {e}")