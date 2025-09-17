import os
import logging
from dataclasses import dataclass
from typing import Optional, Any

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

@dataclass
class SessionData:
    """会话所需数据"""
    session_id: str
    url: str
    access_token: str

@dataclass
class StartResult:
    """API 调用的通用返回结果"""
    code: int
    message: str
    data: Optional[Any] = None # data 在 TS 中是 null，这里用 Optional[Any]

class FxHumanApiClient:
    """
    用于与 FxHuman 流式 API 交互的客户端。
    """

    def __init__(self, token: str, session_id: str):
        """
        初始化 FxHumanApiClient。

        Args:
            token: 用于认证的 API 令牌。
            session_id: 当前会话的 ID。
        """
        if not token or not session_id:
            raise ValueError("FxHumanApiClient 需要 token 和 sessionId")

        self._token = token
        self._session_id = session_id
        self._base_url = os.getenv("NEXT_PUBLIC_BASE_API_URL")

        if not self._base_url:
            raise ValueError("环境变量 NEXT_PUBLIC_BASE_API_URL 未设置")

        # 创建一个可复用的异步 HTTP 客户端实例
        # 这比每次请求都创建一个新客户端更高效
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
        )

    async def start(self, session_data: SessionData) -> StartResult:
        """
        开启一个流式会话房间。

        Args:
            session_data: 会话所需的数据。

        Returns:
            API 返回的 StartResult 对象。

        Raises:
            Exception: 如果 API 请求失败。
        """
        logging.info("[API Client] 开启房间")
        try:
            response = await self._client.post(
                "/v1/streaming.start",
                json={"session_id": session_data.session_id},
            )
            # 这会检查响应状态码是否为 2xx，如果不是，则抛出 HTTPStatusError 异常
            response.raise_for_status()

            # httpx 会自动处理 JSON 解析
            result_data = response.json()
            return StartResult(**result_data)
        except httpx.HTTPStatusError as e:
            error_text = e.response.json()
            logging.error(f"[Error] 创建 HeyGen 房间准备失败: {error_text}")
            raise Exception("[API Client] 创建 HeyGen 房间准备失败") from e
        except httpx.RequestError as e:
            logging.error(f"[Error] 网络请求失败: {e}")
            raise Exception(f"[API Client] 网络请求失败: {e}") from e

    async def send_task(self, text: str) -> StartResult:
        """
        发送一个任务（例如，文本消息）到流式会话。

        Args:
            text: 要发送的文本内容。

        Returns:
            API 返回的 StartResult 对象。

        Raises:
            Exception: 如果 API 请求失败。
        """
        logging.info(f'[API Client] 发送消息: "{text}"')
        try:
            response = await self._client.post(
                "/v1/streaming.task",
                json={
                    "session_id": self._session_id,
                    "text": text,
                    "task_type": "repeat",  # 'talk' or 'repeat'
                },
            )
            response.raise_for_status()

            result_data = response.json()
            logging.info(f"[API Client] 任务已发送 (session: {self._session_id}): \"{text}\"")
            logging.info(f"[API Client] 任务响应: {result_data}")
            return StartResult(**result_data)
        except httpx.HTTPStatusError as e:
            error_data = e.response.json()
            logging.error(f"[API Client] 发送任务到 HeyGen 失败: {error_data}")
            raise Exception("[API Client] 发送任务到 HeyGen 失败") from e
        except httpx.RequestError as e:
            logging.error(f"[API Client] 网络请求失败: {e}")
            raise Exception(f"[API Client] 网络请求失败: {e}") from e


    async def close(self):
        """
        关闭底层的 HTTP 客户端，释放资源。
        在应用程序结束时调用此方法是个好习惯。
        """
        await self._client.aclose()