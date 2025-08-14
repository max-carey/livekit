import asyncio
import base64
import os
from dotenv import load_dotenv
from livekit.agents import Agent, ChatContext, function_tool
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
from typing import List, Dict, Any

@dataclass
class LexicalSense:
    """Represents one meaning/sense of a lexical item"""
    sense_number: int
    definition: str
    examples: List[str]
    explained: bool = False  # Track if user has explained this sense

@dataclass
class TargetLexicalItem:
    """Represents a multi-sense lexical item"""
    phrase: str
    senses: List[LexicalSense]
    
    @property
    def total_senses(self) -> int:
        return len(self.senses)
    
    @property
    def explained_senses(self) -> List[LexicalSense]:
        return [sense for sense in self.senses if sense.explained]
    
    @property
    def remaining_senses(self) -> List[LexicalSense]:
        return [sense for sense in self.senses if not sense.explained]
    
    @property
    def all_explained(self) -> bool:
        return len(self.explained_senses) == self.total_senses
    
    def mark_sense_explained(self, sense_number: int) -> bool:
        """Mark a sense as explained. Returns True if found and marked."""
        for sense in self.senses:
            if sense.sense_number == sense_number:
                sense.explained = True
                return True
        return False

@dataclass
class MySessionInfo:
    user_name: str | None = None
    age: int | None = None
    target_lexical_item: TargetLexicalItem | None = None

load_dotenv()

def create_target_lexical_item(phrase: str, senses_data: List[Dict[str, Any]]) -> TargetLexicalItem:
    """Helper function to create a TargetLexicalItem from dictionary data.
    
    Args:
        phrase: The lexical item phrase (e.g., "SETTLE DOWN")
        senses_data: List of dictionaries with keys: senseNumber, definition, examples
    
    Returns:
        TargetLexicalItem instance
    """
    senses = []
    for sense_dict in senses_data:
        sense = LexicalSense(
            sense_number=sense_dict["senseNumber"],
            definition=sense_dict["definition"],
            examples=sense_dict["examples"]
        )
        senses.append(sense)
    
    return TargetLexicalItem(phrase=phrase, senses=senses)

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
    async def correct_sense_explained(self, sense_number: int, congratulation_message: str) -> str:
        """Call this tool when the user correctly explains one sense of the target lexical item.
        
        Args:
            sense_number: The sense number (1, 2, etc.) that was correctly explained
            congratulation_message: A congratulatory message in Spanish for this specific sense
        """
        print(f"✅ Tool executed: correct_sense_explained for sense {sense_number}")
        
        # Get session data
        session_info = self.session.userdata
        if not session_info or not session_info.target_lexical_item:
            return "Error: No target lexical item found in session."
        
        # Mark this sense as explained
        target_item = session_info.target_lexical_item
        if target_item.mark_sense_explained(sense_number):
            print(f"✅ Marked sense {sense_number} as explained")
            
            # Check if all senses are now explained
            if target_item.all_explained:
                return f"{congratulation_message} ¡Excelente! Has explicado todos los significados de '{target_item.phrase}'. ¡Sesión completada!"
            else:
                remaining = target_item.remaining_senses
                remaining_numbers = [str(s.sense_number) for s in remaining]
                return f"{congratulation_message} Muy bien, pero '{target_item.phrase}' tiene otro significado. ¿Puedes explicar el otro significado de esta frase?"
        else:
            return f"Error: Sense {sense_number} not found."

    @function_tool()
    async def wrong_answer(self, explanation_message: str) -> str:
        """Call this tool when the user answers incorrectly explains the target lexical item.
        
        Args:
            explanation_message: An explanation message in Spanish about why the answer was wrong and ending the session
        """
        print("❌ Tool executed: wrong_answer")
        return f"{explanation_message} La sesión ha terminado."
    
    @function_tool()
    async def all_senses_completed(self, final_congratulation: str) -> str:
        """Call this tool when the user has successfully explained all senses of the target lexical item.
        
        Args:
            final_congratulation: A final congratulatory message in Spanish
        """
        print("🎉 Tool executed: all_senses_completed")
        return f"{final_congratulation} ¡Has completado exitosamente la explicación de todos los significados!"
        
    async def on_enter(self) -> None:
        """Hook called when this agent becomes active."""
        print("NativeExplainAgent on_enter")
        
        # Get the target lexical item from session data
        session_info = self.session.userdata
        if session_info and session_info.target_lexical_item:
            target_item = session_info.target_lexical_item
            instructions = f"""The TARGET LEXICAL ITEM IS '{target_item.phrase}'. This phrasal verb has {target_item.total_senses} different meanings. 

Ask the user to explain what this phrasal verb means. When they explain a meaning, determine which of the {target_item.total_senses} senses they are explaining and whether it's correct.

The {target_item.total_senses} senses are:
"""
            for sense in target_item.senses:
                instructions += f"{sense.sense_number}. {sense.definition} (Example: {sense.examples[0]})\n"
            
            instructions += f"\nStart by asking them to explain what '{target_item.phrase}' means."
            
            await self.session.generate_reply(instructions=instructions)
        else:
            # Fallback if no target item is set
            await self.session.generate_reply(
                instructions="The TARGET LEXICAL ITEM IS 'SETTLE DOWN', ask the user to explain what this phrasal verb means"
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
    
    # Create the SETTLE DOWN example with multiple senses using your data format
    settle_down_data = [
        {
            "senseNumber": 1,
            "definition": "Adopt a quieter and steadier lifestyle",
            "examples": [
                "I just want to fall in love with the right guy and settle down."
            ]
        },
        {
            "senseNumber": 2,
            "definition": "Become calmer, quieter, more orderly",
            "examples": [
                "We need things to settle down before we can make a serious decision."
            ]
        }
    ]
    
    target_item = create_target_lexical_item("SETTLE DOWN", settle_down_data)
    
    session = AgentSession(userdata=MySessionInfo(
        user_name="Max", 
        age=25,
        target_lexical_item=target_item
    ))
    
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