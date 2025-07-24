from dotenv import load_dotenv
from livekit.plugins import elevenlabs
from livekit.agents import Agent, ChatContext, AgentSession, function_tool, RunContext
from livekit import agents
from livekit.agents import RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from instructions import HOST_INSTRUCTIONS
from l1_l2_agent import L1L2Agent
from l2_l1_agent import L2L1Agent
from typing import Any, Optional

load_dotenv()

class HostAgent(Agent):
    def __init__(self, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(chat_ctx=chat_ctx or ChatContext(), instructions=HOST_INSTRUCTIONS)

    @function_tool()
    async def start_l1_l2_quiz(
        self,
        context: RunContext,
    ) -> Agent:
        """Start the L1 to L2 quiz session."""
        await context.session.say("Let's start the L1 to L2 quiz!")
        return L1L2Agent()

    @function_tool()
    async def start_l2_l1_quiz(
        self,
        context: RunContext,
    ) -> Agent:
        """Start the L2 to L1 quiz session."""
        await context.session.say("Let's start the L2 to L1 quiz!")
        return L2L1Agent(chat_ctx=self.session.chat_ctx)

    @function_tool()
    async def stop_quiz(
        self,
        context: RunContext,
    ) -> None:
        """Stop the quiz session and end the conversation."""
        await context.session.say(
            instructions="Thank you and goodbye"
        )
        await context.session.stop()


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
    initial_ctx.add_message(role="assistant", content="The user's name is Lilian Chavez")

    await session.start(
        room=ctx.room,
        agent=HostAgent(chat_ctx=initial_ctx),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    await session.say("Welcome to Vocab Voice. Say A to start L1 to L2 quiz or B to start L2 to L2 quiz")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))