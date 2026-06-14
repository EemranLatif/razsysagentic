# %% [markdown]
# <h1>RAZ Systems </h1>

# %% [markdown]
# # Welcome to the start of your adventure in Agentic AI

# %% [markdown]
# 
# 
# 
# Click where it says "Select Kernel" near the top right, and select the option called `.venv (Python 3.12.9)` or similar, 

# %%
# First let's do an import. If you get an Import Error, double check that your Kernel is correct..

from dotenv import load_dotenv


# %%
# Next it's time to load the API keys into environment variables
# If this returns false, see the next cell!

load_dotenv(override=True)

# %% [markdown]
# ### Wait, did that just output `False`??
# 
# If so, the most common reason is that you didn't save your `.env` file after adding the key! Be sure to have saved.
# 
# 

# %%
# Check the key - if you're not using OpenAI, check whichever key you're using! Ollama doesn't need a key.

import os
openai_api_key = os.getenv('OPENAI_API_KEY')

if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set - please head to the troubleshooting guide in the setup folder")
    


# %%
# And now - the all important import statement
# If you get an import error - head over to troubleshooting in the Setup folder
# Even for other LLM providers like Gemini, you still use this OpenAI import - see Guide 9 for why

from openai import OpenAI

# %%
# And now we'll create an instance of the OpenAI class
# If you're not sure what it means to create an instance of a class - head over to the guides folder (guide 6)!
# If you get a NameError - head over to the guides folder (guide 6)to learn about NameErrors - always instantly fixable
# If you're not using OpenAI, you just need to slightly modify this - precise instructions are in the AI APIs guide (guide 9)

openai = OpenAI()

# %%
# Create a list of messages in the familiar OpenAI format

messages = [{"role": "user", "content": "What is combination of Backend Services + Vector DB + LLM + SQL DB + API/Tools + workspace called? Be brief don't explain just give answer in one sentence"}]

# %%
# And now call it! Any problems, head to the troubleshooting guide
# This uses GPT 4.1 nano, the incredibly cheap model
# The APIs guide (guide 9) has exact instructions for using even cheaper or free alternatives to OpenAI
# If you get a NameError, head to the guides folder (guide 6) to learn about NameErrors - always instantly fixable

response = openai.chat.completions.create(
    model="gpt-4.1-nano",
    messages=messages
)

print(response.choices[0].message.content)


print(response)

# %% [markdown]
# 


