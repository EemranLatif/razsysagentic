"""
messages.py

Shared message definitions used by every agent.

Reviewer  --->  Researcher
Researcher ---> Reviewer
Both -------> Monitor

All agents import ChatMessage from here.
"""

from dataclasses import dataclass


@dataclass
class ChatMessage:
    """
    Message exchanged between agents.
    """

    sender: str
    content: str
    
class ConversationEnded:
    pass

@dataclass
class ConversationSummary:
    summary: str    