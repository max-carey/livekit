from livekit.agents import Agent, ChatContext, function_tool, RunContext, AudioConfig
from typing import Optional
from prompts.loader import load_prompt
from livekit.plugins import (
    openai,
    elevenlabs,
    deepgram,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import asyncio
from mutagen.mp3 import MP3

class DialogueComprehensionAgent(Agent):
    def __init__(self, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            chat_ctx=chat_ctx or ChatContext(),
            instructions=load_prompt('dialogue_comprehension'),
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(
                voice_id="TX3LPaxmHKxFdv7VOQHJ",
                model="eleven_multilingual_v2"
            ),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )

    async def on_enter(self) -> None:
        """Hook called when this agent becomes active."""
        await self.session.generate_reply(
            instructions="Greet the user in their native language extremeley quickly, and ask very quickly if they are ready to play the dialogue."
        )

    @function_tool()
    async def play_dialogue(
        self,
        context: RunContext,
    ) -> None:
        """Play the dialogue audio and ask for comprehension."""
        # Announce that we're about to play the dialogue
        await context.session.say(text="Playing the dialogue now")
        
        # Get audio file duration
        audio_path = './audios/crap_out.mp3'
        audio = MP3(audio_path)
        duration = audio.info.length  # Duration in seconds
        
        # Create task for sleeping during audio playback
        sleep_task = asyncio.create_task(asyncio.sleep(duration))
        
        # Play the audio file using background audio player with AudioConfig
        audio_config = AudioConfig(audio_path, volume=1.0)
        await context.session.background_audio.play(audio_config)
        
        # Wait for the sleep to complete (which means audio should be done)
        await sleep_task
        
        # Generate the follow-up question after audio completes
        await context.session.generate_reply(
            instructions="Ask the user to explain what was happening in the dialogue, focusing on the target word/phrase."
        )

    @function_tool()
    async def provide_feedback(
        self,
        context: RunContext,
        is_correct: bool,
    ) -> None:
        """Provide feedback on the user's comprehension."""
        if is_correct:
            await context.session.generate_reply(
                instructions="In their native language: Congratulate the user for their correct understanding and explain why this usage is important."
            )
        else:
            await context.session.generate_reply(
                instructions="In their native language: Gently explain what the dialogue was about and help them understand the target word/phrase better."
            )


async def entrypoint(ctx):
    from livekit.agents import AgentSession
    from livekit import agents
    from livekit.agents import RoomInputOptions
    from livekit.plugins import noise_cancellation
    
    session = AgentSession()
    
    initial_ctx = ChatContext()
    initial_ctx.add_message(role="assistant", content="The user's name is Lilian Chavez")

    await session.start(
        room=ctx.room,
        agent=DialogueComprehensionAgent(chat_ctx=initial_ctx),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    from livekit import agents
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))