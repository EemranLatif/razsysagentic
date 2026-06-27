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
    source="researcher"
)


@type_subscription("ai_group")
class ResearchAgent(RoutedAgent):

    def __init__(self):
        super().__init__("ResearchAgent")

    @message_handler
    async def handle_message(
        self,
        message: ChatMessage,
        ctx: MessageContext,
    ) -> None:

        if message.sender != "Reviewer":
            return

        await asyncio.sleep(2)

        if "Explain Agentic AI" in message.content:

            reply = """
Agentic AI is an AI system that can plan,
reason, use tools, and take actions to achieve goals.

Example:
A travel agent AI can search flights,
compare hotels, create itineraries,
and book reservations automatically.
"""

        elif "different from a chatbot" in message.content:

            reply = """
A chatbot mainly answers questions.

An AI Agent can take actions,
use tools and pursue goals.

Example:

Chatbot:
Here are flight options.

Agent:
I found the cheapest flight,
booked it, and emailed your itinerary.
"""

        elif "real-world example" in message.content:

            reply = """
A customer support agent can:

1. Read support tickets
2. Query databases
3. Create refunds
4. Notify customers

The agent performs work,
not just conversation.
"""

        else:
            return

        await self.publish_message(
            ChatMessage(
                sender="Researcher",
                content=reply.strip(),
            ),
            AI_GROUP,
        )


async def main():

    runtime = GrpcWorkerAgentRuntime(
        host_address="localhost:50051"
    )

    await runtime.start()

    await ResearchAgent.register(
        runtime,
        "researcher",
        lambda: ResearchAgent(),
    )

    print("Researcher connected.")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())