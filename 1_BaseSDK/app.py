from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr


load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Ajaz"
        reader = PdfReader("raz/ajaz.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("raz/RazSystems.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
            particularly questions related to {self.name}'s career, background, skills and experience. \
            Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
            You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
            Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
            If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
            If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history):
            # ==========================================================
            # STEP 1: BUILD CONTEXT FOR THE MODEL
            # ==========================================================
            #
            # What we send to the model:
            #
            # 1. System Prompt
            #    - AI identity and role
            #    - Behavioral instructions
            #    - Summary and LinkedIn profile
            #    - Rules for handling unknown questions
            #    - Rules for collecting user contact details
            #
            # 2. Conversation History (provided by Gradio)
            #    - Previous user and assistant messages
            #    - Gives the model short-term memory
            #
            # 3. Current User Message
            #    - The latest question from the user
            #
            # 4. Available Tools
            #    - record_unknown_question()
            #    - record_user_details()
            #
            # NOTE:
            # The model only sees what we explicitly send.
            # It cannot access Python variables, databases,
            # files, or the internet unless exposed via tools.
            #
            # ==========================================================
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            # ======================================================
            # STEP 2: SEND REQUEST TO THE MODEL
            # ======================================================
            #
            # Input to model:
            # - messages
            # - tools
            # - model name
            #
            # Output from model:
            # - assistant response OR
            # - tool call request
            #
            # ======================================================
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            # ======================================================
            # STEP 3: DID THE MODEL REQUEST A TOOL?
            # ======================================================
            if response.choices[0].finish_reason=="tool_calls":
                # Assistant message containing tool request
                message = response.choices[0].message
                # Example:
                # "Call record_user_details(email='abc@test.com') refer below for JSON Version, how it is called literally"
                tool_calls = message.tool_calls
                # Execute Python functions locally
                results = self.handle_tool_call(tool_calls)
                # Add assistant's tool request to conversation
                messages.append(message)   # Single element
                # Add tool execution results to conversation
                messages.extend(results)    # many elements
                # Loop continues:
                # Updated messages are sent back to model
            else:
                done = True
        # ==========================================================
        # STEP 4: RETURN FINAL RESPONSE TO USER
        # ==========================================================        
        return response.choices[0].message.content
    

if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(me.chat).launch()
    
    
    """
    me.chat
    
    history = []

    while True:
        message = get_user_input()

        response = me.chat(message, history)

        history.append((message, response))

        display(response)
    
    """
    
    """
        message → the latest user input
        history → all previous conversation turns
        
        =============================
        User: Hello
        Bot: Hi!

        User: What is Python?
        ==============================

        history =
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        message = What is Python?
    """
    
    
"""
    User Question
        ↓
    Model thinks
        ↓
    ┌──────────────┐
    │ Answer only   │
    │ OR            │
    │ Tool calls    │ ← can be multiple
    └──────────────┘
        ↓
    Your code executes tools
        ↓
    Model continues until final answer
     
   {
    "tool_calls": [
        {
        "function": {
            "name": "record_user_details",
            "arguments": {"email": "a@test.com"}
        }
        },
        {
        "function": {
            "name": "record_unknown_question",
            "arguments": {"question": "pricing?"}
        }
        }
    ]
    } 
    
    Model can also call sequentialle after result sent it reason's again make a second tool call
{
    "tool_calls": [
        {
        "function": {
            "name": "record_user_details",
            "arguments": {"email": "a@test.com"}
        }
       ] 
    """