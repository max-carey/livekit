from livekit.agents import Agent, ChatContext, function_tool, RunContext
from typing import Optional
from instructions import L2_L1_QUIZZER

class L2L1Agent(Agent):
    def __init__(self, chat_ctx: ChatContext) -> None:
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=L2_L1_QUIZZER
        )

    async def on_enter(self) -> None:
        """Hook called when this agent becomes active."""
        await self.session.generate_reply(
            instructions="The TARGET LEXICAL ITEM IS inscribirse, quiz the user about its meaning in their L1"
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