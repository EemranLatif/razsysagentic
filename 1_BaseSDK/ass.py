# %% [markdown]
# <h1>RAZ Systems — Assignment 1</h1>
# 
# ## Topic: Setting Up and Using the OpenAI SDK
# 
# **Instructions:** Work through each task below. Fill in the missing code where you see `# YOUR CODE HERE`. Run each cell to check your work.
# 
# ---

# %% [markdown]
# ### Task 1 — Import the environment loader
# 
# Import the `load_dotenv` function from the `dotenv` package. This is how we load our API keys from a `.env` file.

# %%
# YOUR CODE HERE
# Hint: from ??? import load_dotenv


# %% [markdown]
# ### Task 2 — Load your API keys
# 
# Call `load_dotenv()` with the `override=True` argument. It should print `True` if your `.env` file is found and saved correctly.

# %%
# YOUR CODE HERE


# %% [markdown]
# ### Task 3 — Verify your API key
# 
# Use `os.getenv()` to retrieve your `OPENAI_API_KEY`. Then write an `if/else` block that:
# - Prints the first **9 characters** of the key if it exists
# - Prints a helpful error message if it is not set

# %%
import os

# YOUR CODE HERE — retrieve the key


# YOUR CODE HERE — print the result


# %% [markdown]
# ### Task 4 — Create the OpenAI client
# 
# Import the `OpenAI` class and create an instance of it called `openai`.

# %%
# YOUR CODE HERE


# %% [markdown]
# ### Task 5 — Send a message to the model
# 
# Create a `messages` list with one user message asking:
# 
# > *"What are the three most important things a beginner should know about working with AI APIs? Answer in one sentence each."*
# 
# Then call `openai.chat.completions.create()` using `model="gpt-4.1-nano"` and print the text content of the response.

# %%
# YOUR CODE HERE — build the messages list

# YOUR CODE HERE — call the API and print the response


# %% [markdown]
# ### Task 6 — Inspect the full response object
# 
# Print the **entire** response object (not just `.choices[0].message.content`). Look at the output and answer the questions below in the markdown cell.
# 
# **Questions to answer (edit this cell):**
# 1. What is the value of `finish_reason` in the response? What do you think it means?
# 2. How many `prompt_tokens` were used?
# 3. What is the `model` field showing?

# %%
# YOUR CODE HERE — print the full response


# %% [markdown]
# **Your answers:**
# 1. finish_reason = ??? — it means ...
# 2. prompt_tokens = ???
# 3. model = ???

# %% [markdown]
# ---
# ## ✅ Solution — scroll down only after attempting!
# 
# ---

# %%
# SOLUTION — Task 1
from dotenv import load_dotenv

# %%
# SOLUTION — Task 2
load_dotenv(override=True)

# %%
# SOLUTION — Task 3
import os

openai_api_key = os.getenv('OPENAI_API_KEY')

if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:9]}")
else:
    print("OpenAI API Key not set — check your .env file and make sure it is saved")

# %%
# SOLUTION — Task 4
from openai import OpenAI

openai = OpenAI()

# %%
# SOLUTION — Task 5
messages = [{"role": "user", "content": "What are the three most important things a beginner should know about working with AI APIs? Answer in one sentence each."}]

response = openai.chat.completions.create(
    model="gpt-4.1-nano",
    messages=messages
)

print(response.choices[0].message.content)

# %%
# SOLUTION — Task 6
# Print the full response object so we can inspect every field
print(response)

# Answer guide:
# finish_reason = 'stop'  → the model finished naturally (didn't hit a token limit or get interrupted)
# prompt_tokens          → number of tokens in our user message
# model                  → the exact versioned model name that served the request (e.g. gpt-4.1-nano-2025-04-14)


