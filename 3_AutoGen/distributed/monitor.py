import asyncio

from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
    type_subscription,
)

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime

from messages import ChatMessage


@type_subscription("ai_group")
class MonitorAgent(RoutedAgent):

    def __init__(self):
        super().__init__("Monitor")

    @message_handler
    async def handle_message(
        self,
        message: ChatMessage,
        ctx: MessageContext,
    ) -> None:

        print("\n" + "=" * 60)
        print(f"{message.sender}:")
        print(message.content)
        print("=" * 60)


async def main():

    runtime = GrpcWorkerAgentRuntime(
        host_address="localhost:50051"
    )

    await runtime.start()

    await MonitorAgent.register(
        runtime,
        "monitor",
        lambda: MonitorAgent(),
    )

    print("\nMonitor connected.")
    print("Listening to ai_group...\n")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())