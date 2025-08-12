from dotenv import load_dotenv
from livekit.agents import Agent, ChatContext, AgentSession, function_tool, RunContext, BackgroundAudioPlayer
from livekit import agents
from livekit.agents import RoomInputOptions
from livekit.plugins import (
    openai,
    google,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from agents import NativeExplainAgent, ListenAgent
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
            # Google TTS with Spanish voice - see https://docs.livekit.io/agents/integrations/tts/google/
            tts=google.TTS(
                language="es-US",
                voice_name="es-US-Chirp3-HD-Puck"
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
    async def start_listening_session(
        self,
        context: RunContext,
    ) -> Agent:
        """Start the listening session."""
        await context.session.say("Let's start the listening session!")
        return ListenAgent()

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

    await session.say("Welcome to Vocab Voice. Say A for native explanation or C for listening practice")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))