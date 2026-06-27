"""
monitor.py

Monitor Agent

Responsibilities
----------------
1. Listen to every message on ai_group
2. Display the conversation
3. Save the transcript
4. Detect END_CONVERSATION
5. Send an email summary using SendGrid
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
    EMAIL_TO,
)

from messages import ChatMessage
from sendgrid_tool import SendGridTool


@type_subscription("ai_group")
class MonitorAgent(RoutedAgent):

    def __init__(self):
        super().__init__("MonitorAgent")

        # Stores the full conversation
        self.transcript = []

        # Email tool
        self.email_tool = SendGridTool()

    @message_handler
    async def handle_message(
        self,
        message: ChatMessage,
        ctx: MessageContext,
    ) -> None:

        # -----------------------------
        # Display message
        # -----------------------------

        print()

        print("=" * 70)
        print(message.sender)
        print("-" * 70)
        print(message.content)
        print("=" * 70)

        # Save transcript

        self.transcript.append(
            f"{message.sender}\n{message.content}\n"
        )

        # -----------------------------
        # Conversation finished?
        # -----------------------------

        if message.content == "END_CONVERSATION":

            print("\nConversation completed.")

            transcript = "\n".join(self.transcript)

            summary = self.create_summary()

            print("\nSending email...\n")

            await self.email_tool.send_summary(
                EMAIL_TO,
                summary,
                transcript,
            )

    def create_summary(self):

        """
        Later we'll replace this with GPT.

        For now we return a fixed summary.
        """

        return """
Conversation Summary

• Agentic AI can reason and plan.

• Unlike chatbots,
  AI agents can use tools.

• AI agents perform tasks,
  not just answer questions.

• Example:
  Customer support automation.
"""


async def main():

    runtime = GrpcWorkerAgentRuntime(
        host_address=HOST_ADDRESS
    )

    await runtime.start()

    await MonitorAgent.register(
        runtime,
        "monitor",
        lambda: MonitorAgent(),
    )

    print("Monitor connected.")
    print("Listening for conversation...")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())