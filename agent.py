from dotenv import load_dotenv
import json
from livekit.plugins import elevenlabs
from livekit.agents import Agent, ChatContext, AgentSession

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from instructions import ASSISTANT_INSTRUCTIONS
from typing import Any

load_dotenv()


class Assistant(Agent):
    def __init__(self, chat_ctx: ChatContext) -> None:
        super().__init__(chat_ctx=chat_ctx, instructions=ASSISTANT_INSTRUCTIONS)

    async def on_enter(self):
        print("hello")
        # await self.session.generate_reply(
        #     instructions="Be extremeley direct, Say I [laugh] love pizza",
        # )

    @function_tool()
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
    ) -> dict[str, Any]:
        """Look up weather information for a given location.
        
        Args:
            location: The location to look up weather information for.
        """

        return {"weather": "sunny", "temperature_f": 70}


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            model="eleven_multilingual_v2"
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    initial_ctx = ChatContext()
    initial_ctx.add_message(role="assistant", content=f"The user's name is Max")

    await session.start(
        room=ctx.room,
        agent=Assistant(chat_ctx=initial_ctx),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )

    

    await ctx.connect()

    await session.generate_reply(
        instructions="Greet the user by name and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))