# src/agent.py
import asyncio
import json
import logging
from typing import AsyncIterable
import os

from dotenv import load_dotenv
from livekit.agents import (
    JobContext,
    JobProcess,
    JobRequest,
    WorkerOptions,
    RoomOutputOptions,
    cli,
    llm,
    voice,
)
from livekit.plugins import openai, silero
from livekit.agents.llm import ImageContent, AudioContent
from livekit.agents import Agent

from module.firstx_human import FxHumanApiClient
from module.sentence_processor import SentenceStreamProcessor

load_dotenv(".env.local")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fx-assistant")

class FxAssistant(voice.Agent):
    def __init__(self, api_client: FxHumanApiClient):
        super().__init__(
            instructions="You are a helpful voice AI assistant.",
        )
        self.api_client = api_client

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tool_ctx: llm.ToolContext,
        model_settings: voice.ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk]:
        """
        重写 llm_node 以拦截 LLM 输出流。
        """
        original_stream = super().llm_node(chat_ctx, tool_ctx, model_settings)
        sentence_processor = SentenceStreamProcessor()

        async for chunk in original_stream:
            yield chunk

            if chunk.delta.content:
                sentences = sentence_processor.process(chunk.delta.content)
                for sentence in sentences:
                    logger.info(f'[FxAssistant] [Sentence] 输出完整句子: "{sentence}"')
                    asyncio.create_task(self.api_client.send_task(sentence))

        remaining_text = sentence_processor.flush()
        if remaining_text:
            logger.info(f'[FxAssistant] [Sentence] 输出结尾部分: "{remaining_text}"')
            asyncio.create_task(self.api_client.send_task(remaining_text))

def prewarm(proc: JobProcess):
    """在 Agent 启动工作前预加载资源。"""
    logger.info("[Agent] Prewarming VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("[Agent] VAD model loaded.")

async def entrypoint(ctx: JobContext):
    """入口点"""
    metadata = json.loads(ctx.job.metadata or "{}")
    logger.info(f"[Agent] Received job with metadata: {metadata}")

    token = metadata.get("token", "")
    session_id = metadata.get("sessionId", "")
    api_client = FxHumanApiClient(token=token, session_id=session_id)
    
    session = voice.AgentSession(
        # vad=ctx.proc.userdata["vad"],
        # stt=openai.STT(model="whisper-1"),
        # llm=openai.LLM(model="gpt-4o-mini"),
        # tts=openai.TTS(model="tts-1", voice="alloy"),
        llm=openai.realtime.RealtimeModel(),
    )

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: voice.ConversationItemAddedEvent):
        """
        当消息提交到历史消息的时候
        """
        logger.info(f"Conversation item added from {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}")
        for content in event.item.content:
            if isinstance(content, str):
                logger.info(f" - text: {content}")
            elif isinstance(content, ImageContent):
                logger.info(f" - image: {content.image}")
            elif isinstance(content, AudioContent):
                logger.info(f" - audio: {content.frame}, transcript: {content.transcript}")

    fx_assistant = FxAssistant(api_client=api_client)

    await session.start(
        # agent=fx_assistant,
        agent=Agent(instructions="You are a helpful voice AI assistant."),
        room=ctx.room,
        room_output_options=RoomOutputOptions(audio_enabled=False),
    )

    await ctx.connect()
    logger.info(f"[Agent] Connected to room {ctx.room.name}, waiting for participant...")

async def request_fnc(req: JobRequest):
    await req.accept(
        name="agent-fx-human-ai",
        identity=os.getenv("AGENT_IDENTITY", "agent-fx-human-ai-identity"),
        attributes={"agent": "fx-human-ai"},
        metadata="{'agent': 'fx-human-ai'}",
    )

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=request_fnc,
            prewarm_fnc=prewarm,
            agent_name=os.getenv("AGENT_NAME", "firstx01"),
        )
    )
