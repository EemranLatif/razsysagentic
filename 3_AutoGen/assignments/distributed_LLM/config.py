"""
config.py

Central location for all application configuration.

Every agent imports values from here instead of
hardcoding them.

If you want to change the model, host address,
topic name or conversation delay, change it here.
"""

from autogen_core import TopicId

# ---------------------------------------------------------
# gRPC Host
# ---------------------------------------------------------

HOST_ADDRESS = "localhost:50051"

# ---------------------------------------------------------
# Topic
# ---------------------------------------------------------

TOPIC_NAME = "ai_group"

# AutoGen 0.4.9.x requires both type and source.
AI_GROUP_TOPIC = TopicId(
    type=TOPIC_NAME,
    source="system",
)

# ---------------------------------------------------------
# OpenAI
# ---------------------------------------------------------

MODEL_NAME = "gpt-4o-mini"

# ---------------------------------------------------------
# Conversation
# ---------------------------------------------------------

# Delay between messages (seconds)
MESSAGE_DELAY = 2

# Maximum number of reviewer follow-up questions.
MAX_TURNS = 3

# ---------------------------------------------------------
# Email Summary
# ---------------------------------------------------------

EMAIL_TO = "student@example.com"

EMAIL_SUBJECT = "AI Agent Conversation Summary"