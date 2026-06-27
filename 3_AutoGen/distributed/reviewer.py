import asyncio

from autogen_core import (
    MessageContext,
    RoutedAgent,
    TopicId,
    message_handler,
    type_subscription,
)

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime

from messages import ChatMessage


AI_GROUP = TopicId(
    type="ai_group",
    source="system"
)


@type_subscription("ai_group")
class ReviewerAgent(RoutedAgent):

    def __init__(self):
        super().__init__("ReviewerAgent")

    @message_handler
    async def handle_message(
        self,
        message: ChatMessage,
        ctx: MessageContext,
    ) -> None:

        if message.sender != "Researcher":
            return

        await asyncio.sleep(2)

        if "Agentic AI is an AI system" in message.content:

            await self.publish_message(
                ChatMessage(
                    sender="Reviewer",
                    content="How is that different from a chatbot?",
                ),
                AI_GROUP,
            )

        elif "A chatbot mainly answers questions" in message.content:

            await self.publish_message(
                ChatMessage(
                    sender="Reviewer",
                    content="Give a real-world example.",
                ),
                AI_GROUP,
            )


async def main():

    runtime = GrpcWorkerAgentRuntime(
        host_address="localhost:50051"
    )

    await runtime.start()

    await ReviewerAgent.register(
        runtime,
        "reviewer",
        lambda: ReviewerAgent(),
    )

    print("Reviewer connected.")

    await asyncio.sleep(10)

    await runtime.publish_message(
        ChatMessage(
            sender="Reviewer",
            content="Explain Agentic AI.",
        ),
        AI_GROUP,
    )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())