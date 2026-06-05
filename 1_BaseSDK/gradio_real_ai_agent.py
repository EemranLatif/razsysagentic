import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ai_agent_chat(message, history):
    messages = []

    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages
    )

    return response.choices[0].message.content


demo = gr.ChatInterface(
    fn=ai_agent_chat,
    title="AI Agent Chatbot",
    description="A Gradio chatbot powered by GPT"
)

if __name__ == "__main__":
    demo.launch()