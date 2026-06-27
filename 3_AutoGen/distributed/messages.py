from dataclasses import dataclass


@dataclass
class ChatMessage:
    sender: str
    content: str