from dotenv import load_dotenv
from livekit.agents import Agent, ChatContext, function_tool, RunContext
from typing import Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.loader import load_prompt
from hello_world_graph import create_workflow
from livekit.plugins import (
    google,
    deepgram,
    silero,
    langchain,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()

class NativeExplainAgent(Agent):
    def __init__(self, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            chat_ctx=chat_ctx or ChatContext(),
            instructions=load_prompt('native_explain'),
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=langchain.LLMAdapter(
                graph=create_workflow()
            ),
            tts=google.TTS(
                language="es-US",
                voice_name="es-US-Chirp3-HD-Puck"
            ),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )
        
    async def on_enter(self) -> None:
        """Hook called when this agent becomes active."""
        print("NativeExplainAgent on_enter")
        await self.session.generate_reply(
            instructions="The TARGET LEXICAL ITEM IS 'GO ON', ask the user to explain what this phrasal verb means"
        )

    @function_tool()
    async def correct_answer(
        self,
        context: RunContext,
    ) -> None:
        """Call this tool when the user answers correctly."""
        await context.session.generate_reply(
            instructions="In Spanish: Congratulate the user enthusiastically for their correct answer!"
        )

    @function_tool()
    async def wrong_answer(
        self,
        context: RunContext,
    ) -> None:
        """Call this tool when the user answers incorrectly."""
        await context.session.generate_reply(
            instructions="In Spanish: Gently encourage the user to try again and don't give up!"
        )


async def entrypoint(ctx):
    from livekit.agents import AgentSession
    from livekit import agents
    from livekit.agents import RoomInputOptions
    from livekit.plugins import noise_cancellation
    
    session = AgentSession()
    
    initial_ctx = ChatContext()
    initial_ctx.add_message(role="assistant", content="The user's name is Roberto")

    await session.start(
        room=ctx.room,
        agent=NativeExplainAgent(chat_ctx=initial_ctx),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    from livekit import agents
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))