import asyncio
import base64
import os
from dotenv import load_dotenv
from livekit.agents import Agent, ChatContext, function_tool
from livekit import api
from typing import Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.loader import load_prompt
from livekit.plugins import (
    google,
    deepgram,
    silero,
    openai,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.metrics import LLMMetrics, STTMetrics, TTSMetrics, EOUMetrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from livekit.agents.telemetry import set_tracer_provider

from livekit.agents import AgentSession
from dataclasses import dataclass

@dataclass
class MySessionInfo:
    user_name: str | None = None
    age: int | None = None

load_dotenv()

def setup_langfuse(
    host: str | None = None, public_key: str | None = None, secret_key: str | None = None
):
    

    public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    host = host or os.getenv("LANGFUSE_HOST")

    if not public_key or not secret_key or not host:
        raise ValueError("LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST must be set")

    langfuse_auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{host.rstrip('/')}/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

    trace_provider = TracerProvider()
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    set_tracer_provider(trace_provider)

class NativeExplainAgent(Agent):
    def __init__(self, chat_ctx: Optional[ChatContext] = None, room_name: Optional[str] = None) -> None:
        self._room_name = room_name
        
        stt = deepgram.STT(model="nova-3", language="multi")
        tts = google.TTS(
            language="es-US",
            voice_name="es-US-Chirp3-HD-Puck"
        )
        llm=openai.LLM(model="gpt-4o-mini")
        super().__init__(
            chat_ctx=chat_ctx or ChatContext(),
            instructions=load_prompt('native_explain'),
            llm=llm,
            stt=stt,
            tts=tts,
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel()
        )

        def llm_metrics_wrapper(metrics: LLMMetrics):
            asyncio.create_task(self.on_llm_metrics_collected(metrics))
        llm.on("metrics_collected", llm_metrics_wrapper)

        def stt_metrics_wrapper(metrics: STTMetrics):
            asyncio.create_task(self.on_stt_metrics_collected(metrics))
        stt.on("metrics_collected", stt_metrics_wrapper)

        def eou_metrics_wrapper(metrics: EOUMetrics):
            asyncio.create_task(self.on_eou_metrics_collected(metrics))
        stt.on("eou_metrics_collected", eou_metrics_wrapper)

        def tts_metrics_wrapper(metrics: TTSMetrics):
            asyncio.create_task(self.on_tts_metrics_collected(metrics))
        tts.on("metrics_collected", tts_metrics_wrapper)

    @function_tool()
    async def correct_answer(self) -> str:
        """Call this tool when the user answers correctly explains the target lexical item"""
        print("✅ Tool executed: correct_answer")
        await self.session.generate_reply(
            instructions="Congratulate the user in Spanish and ask for the next word"
        )
        return "The user answered correctly!"

    @function_tool()
    async def wrong_answer(self) -> str:
        """Call this tool when the user answers incorrectly explains the target lexical item"""
        print("❌ Tool executed: wrong_answer")
        
        if self._room_name:
            api_client = api.LiveKitAPI(
                os.getenv("LIVEKIT_URL"),
                os.getenv("LIVEKIT_API_KEY"),
                os.getenv("LIVEKIT_API_SECRET"),
            )
            try:
                await api_client.room.delete_room(api.DeleteRoomRequest(
                    room=self._room_name,
                ))
                print(f"Successfully deleted room: {self._room_name}")
            except Exception as e:
                print(f"Failed to delete room {self._room_name}: {e}")
        
        return "The user answered incorrectly. Session ended."
        
    async def on_enter(self) -> None:
        """Hook called when this agent becomes active."""
        print("NativeExplainAgent on_enter")
        await self.session.generate_reply(
            instructions="The TARGET LEXICAL ITEM IS 'MULL OVER', ask the user to explain what this phrasal verb means"
        )
    async def on_stt_metrics_collected(self, metrics: STTMetrics) -> None:
        print("\n--- STT Metrics ---")
        print(f"Duration: {metrics.duration:.4f}s")
        print(f"Audio Duration: {metrics.audio_duration:.4f}s")
        print(f"Streamed: {'Yes' if metrics.streamed else 'No'}")
        print("------------------\n")

    async def on_eou_metrics_collected(self, metrics: EOUMetrics) -> None:
        print("\n--- End of Utterance Metrics ---")
        print(f"End of Utterance Delay: {metrics.end_of_utterance_delay:.4f}s")
        print(f"Transcription Delay: {metrics.transcription_delay:.4f}s")
        print("--------------------------------\n")

    async def on_tts_metrics_collected(self, metrics: TTSMetrics) -> None:
        print("\n--- TTS Metrics ---")
        print(f"TTFB: {metrics.ttfb:.4f}s")
        print(f"Duration: {metrics.duration:.4f}s")
        print(f"Audio Duration: {metrics.audio_duration:.4f}s")
        print(f"Streamed: {'Yes' if metrics.streamed else 'No'}")
        print("------------------\n")
    
    async def on_llm_metrics_collected(self, metrics: LLMMetrics) -> None:
        print("\n--- LLM Metrics ---")
        print(f"Prompt Tokens: {metrics.prompt_tokens}")
        print(f"Completion Tokens: {metrics.completion_tokens}")
        print(f"Tokens per second: {metrics.tokens_per_second:.4f}")
        print(f"TTFT New: {metrics.ttft:.4f}s")
        print("------------------\n")


async def entrypoint(ctx):
    setup_langfuse()  # set up the langfuse tracer provider
    
    from livekit.agents import AgentSession
    from livekit import agents
    from livekit.agents import RoomInputOptions
    from livekit.plugins import noise_cancellation
    
    session = AgentSession(userdata=MySessionInfo(user_name="Max", age=25))
    
    initial_ctx = ChatContext()
    initial_ctx.add_message(role="assistant", content="The user's name is Max")

    await session.start(
        room=ctx.room,
        agent=NativeExplainAgent(chat_ctx=initial_ctx, room_name=ctx.room.name),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    from livekit import agents
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))