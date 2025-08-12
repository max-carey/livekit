from dotenv import load_dotenv
from livekit.plugins import elevenlabs
from livekit.agents import Agent, ChatContext, AgentSession, function_tool, RunContext, BackgroundAudioPlayer
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
from native_explain_agent import NativeExplainAgent
from l2_l1_agent import L2L1Agent
from dialogue_comprehension_agent import DialogueComprehensionAgent
from typing import Any, Optional
from prompts.loader import load_prompt

load_dotenv()

class HostAgent(Agent):
    def __init__(self, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            chat_ctx=chat_ctx or ChatContext(),
            instructions=load_prompt('host'),
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(
                voice_id="21m00Tcm4TlvDq8ikWAM",
                model="eleven_multilingual_v2"
            ),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )

    @function_tool()
    async def start_native_explain(
        self,
        context: RunContext,
    ) -> Agent:
        """Start the native explanation session."""
        await context.session.say("Let's start the native explanation session!")
        return NativeExplainAgent()

    @function_tool()
    async def start_l2_l1_quiz(
        self,
        context: RunContext,
    ) -> Agent:
        """Start the L2 to L1 quiz session."""
        await context.session.say("Let's start the L2 to L1 quiz!")
        return L2L1Agent(chat_ctx=self.session.chat_ctx)

    @function_tool()
    async def start_dialogue_comprehension(
        self,
        context: RunContext,
    ) -> Agent:
        """Start the dialogue comprehension session."""
        await context.session.say("Let's practice dialogue comprehension!")
        return DialogueComprehensionAgent()

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
    session = AgentSession()
    
    # Create the background audio player
    background_audio = BackgroundAudioPlayer()
    
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
    
    # Start the background audio player
    await background_audio.start(room=ctx.room, agent_session=session)
    
    # Store the background_audio player in the session for access by other agents
    session.background_audio = background_audio

    await session.say("Welcome to Vocab Voice. Say A for native explanation, B for L2 to L1 quiz, or C for dialogue comprehension")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))