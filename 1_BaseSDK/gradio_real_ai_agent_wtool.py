import os
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



SERPER_API_KEY = os.environ["SERPER_API_KEY"]


def get_real_weather(city):
    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": f"weather in {city}"
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    # Extract snippet from search results
    try:
        answer = data["organic"][0]["snippet"]
        return f"Weather info for {city}: {answer}"
    except Exception:
        return "Could not fetch weather information."

# --------------------
# Tools
# --------------------
def get_weather(city):
    return f"The weather in {city} is 72°F and sunny."


def calculate(expression):
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_real_weather",
            "description": "Get weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    }
]


import json

def ai_agent_chat(message, history):

    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant. Use tools whenever needed."
        }
    ]

    # -----------------------------
    # SAFE HISTORY HANDLING
    # -----------------------------
    for h in history:

        # Case 1: (user, assistant)
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            messages.append({"role": "user", "content": h[0]})
            messages.append({"role": "assistant", "content": h[1]})

        # Case 2: OpenAI-style dict
        elif isinstance(h, dict):
            role = h.get("role")
            content = h.get("content")
            if role and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    # -----------------------------
    # FIRST LLM CALL (tool decision)
    # -----------------------------
    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages,
        tools=TOOLS
    )

    assistant_message = response.choices[0].message

    # -----------------------------
    # TOOL CALL HANDLING
    # -----------------------------
    if assistant_message.tool_calls:

        tool_call = assistant_message.tool_calls[0]
        tool_name = tool_call.function.name

        args = json.loads(tool_call.function.arguments)

        if tool_name == "get_weather":
            tool_result = get_weather(args["city"])

        elif tool_name == "calculate":
            tool_result = calculate(args["expression"])

        else:
            tool_result = "Unknown tool"

        # Add assistant tool request
        messages.append(assistant_message)

        # Add tool result
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result
        })

        # Final response after tool execution
        final_response = client.chat.completions.create(
            model="gpt-5",
            messages=messages
        )

        return final_response.choices[0].message.content

    # No tool needed
    return assistant_message.content





# --------------------
# UI
# --------------------
demo = gr.ChatInterface(
    fn=ai_agent_chat,
    title="Agentic AI Chatbot",
    description="GPT + Tool Calling"
)

if __name__ == "__main__":
    demo.launch()