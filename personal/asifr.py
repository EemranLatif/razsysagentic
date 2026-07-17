import asyncio
from dataclasses import dataclass

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv


load_dotenv(override=True)


@dataclass
class Message:
    content: str


class ComedianAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("ComedianAgent")
        model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
        self._delegate = AssistantAgent(
            "ComedianAgent",
            model_client=model_client,
            system_message=(
                "You are a witty, family-friendly comedian. "
                "Write one short joke, two sentences max."
            ),
        )

    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        print(f"{self.id.type} received topic: {message.content}")
        text_message = TextMessage(content=message.content, source="user")
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)
        joke = response.chat_message.content
        print(f"{self.id.type} wrote: {joke}")
        return Message(content=joke)


class WordCounterAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("WordCounterAgent")
        # No model client here: this agent is plain Python only.

    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        print(f"{self.id.type} received: {message.content}")
        word_count = len(message.content.split())
        report = f"({word_count} words) {message.content}"
        return Message(content=report)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    try:
        await ComedianAgent.register(runtime, "comedian", lambda: ComedianAgent())
        await WordCounterAgent.register(runtime, "word_counter", lambda: WordCounterAgent())

        runtime.start()

        comedian_id = AgentId("comedian", "default")
        counter_id = AgentId("word_counter", "default")

        joke_response = await runtime.send_message(Message(content="cats"), comedian_id)
        print(">>> Joke:", joke_response.content)

        count_response = await runtime.send_message(Message(content=joke_response.content), counter_id)
        print(">>> Word count report:", count_response.content)
    finally:
        await runtime.stop()
        await runtime.close()


if __name__ == "__main__":
    asyncio.run(main())
