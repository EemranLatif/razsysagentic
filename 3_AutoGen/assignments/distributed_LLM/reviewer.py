"""
reviewer.py

Reviewer Agent

Responsibilities
----------------
1. Start the conversation
2. Ask follow-up questions
3. Stop after MAX_TURNS
"""

import asyncio

from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
    type_subscription,
)

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime

from config import (
    HOST_ADDRESS,
    AI_GROUP_TOPIC,
    MESSAGE_DELAY,
    MAX_TURNS,
)

from messages import ChatMessage, ConversationEnded


@type_subscription("ai_group")
class ReviewerAgent(RoutedAgent):

    def __init__(self):
        super().__init__("ReviewerAgent")

        self.turn = 0

    @message_handler
    async def handle_message(
        self,
        message: ChatMessage,
        ctx: MessageContext,
    ) -> None:

        # Ignore our own messages
        if message.sender != "Researcher":
            return

        print("\nResearcher replied:")
        print(message.content)

        self.turn += 1

        if self.turn >= MAX_TURNS:

            print("\nConversation finished.\n")

            await self.publish_message(
                ChatMessage(
                    sender="Reviewer",
                    content="END_CONVERSATION",
                ),
                AI_GROUP_TOPIC,
            )


            return

        await asyncio.sleep(MESSAGE_DELAY)

        if self.turn == 1:

            question = "How is that different from a chatbot?"

        elif self.turn == 2:

            question = "Give a real-world example."

        else:

            question = "Thank you."

        print("\nReviewer asking:")
        print(question)

        await self.publish_message(
            ChatMessage(
                sender="Reviewer",
                content=question,
            ),
            AI_GROUP_TOPIC,
        )


async def main():

    runtime = GrpcWorkerAgentRuntime(
        host_address=HOST_ADDRESS
    )

    await runtime.start()

    await ReviewerAgent.register(
        runtime,
        "reviewer",
        lambda: ReviewerAgent(),
    )

    print("Reviewer connected.")

    #
    # Start the conversation
    #
    await asyncio.sleep(2)

    print("\nStarting conversation...\n")

    await runtime.publish_message(
        ChatMessage(
            sender="Reviewer",
            content="Explain Agentic AI.",
        ),
        AI_GROUP_TOPIC,
    )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())