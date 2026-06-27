"""
researcher.py

Research Agent

Responsibilities
----------------
1. Subscribe to ai_group
2. Receive Reviewer questions
3. Generate an answer
4. Publish the answer back to ai_group
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
)

from messages import ChatMessage


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

        # Ignore our own messages
        if message.sender != "Reviewer":
            return
        
        # Stop the conversation
        if message.content == "END_CONVERSATION":
            print("Researcher stopping...")
            return        

        print(f"\nReviewer asked:\n{message.content}")

        # Simulate thinking
        await asyncio.sleep(MESSAGE_DELAY)

        # -------------------------------------------------
        # Temporary hardcoded responses.
        # Replace this section with an LLM later.
        # -------------------------------------------------

        if "Explain Agentic AI" in message.content:

            answer = """
Agentic AI is an AI system capable of planning,
reasoning, using tools and taking actions
to accomplish goals.

Example:

A travel planning agent can search flights,
compare hotels, build an itinerary and
book reservations automatically.
"""

        elif "different from a chatbot" in message.content.lower():

            answer = """
A chatbot mainly responds to user questions.

An AI Agent goes beyond conversation.

It can:

• Plan tasks
• Use external tools
• Make decisions
• Complete work

Example:

Chatbot:
"Here are flight options."

AI Agent:
"I found the cheapest flight,
booked it and emailed your itinerary."
"""

        elif "real-world example" in message.content.lower():

            answer = """
Example:

Customer Support Agent

1. Reads support ticket

2. Looks up customer information
   from a database

3. Creates refund

4. Sends confirmation email

Unlike a chatbot,
it actually performs work.
"""

        else:

            answer = "Could you please clarify your question?"

        # -------------------------------------------------

        print("\nResearcher answering...")

        await self.publish_message(
            ChatMessage(
                sender="Researcher",
                content=answer.strip(),
            ),
            AI_GROUP_TOPIC,
        )


async def main():

    runtime = GrpcWorkerAgentRuntime(
        host_address=HOST_ADDRESS
    )

    await runtime.start()

    await ResearchAgent.register(
        runtime,
        "researcher",
        lambda: ResearchAgent(),
    )

    print("Researcher connected.")
    print("Waiting for Reviewer...")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())