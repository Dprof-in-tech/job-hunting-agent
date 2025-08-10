"""
Utility functions for the job hunting multi-agent system
"""

from langchain_core.messages import BaseMessage
from typing import Any, Dict, List, Union


def serialize_message(message: Any) -> str:
    """Convert any message type to a serializable string"""
    if isinstance(message, BaseMessage):
        return str(message.content)
    elif isinstance(message, str):
        return message
    else:
        return str(message)


def serialize_messages(messages: List[Any]) -> List[str]:
    """Convert a list of messages to serializable strings"""
    return [serialize_message(msg) for msg in messages]


def make_serializable(data: Dict[str, Any]) -> Dict[str, Any]:
    """Make a dictionary fully serializable by converting AIMessage objects"""
    if not isinstance(data, dict):
        return data
    
    serialized = {}
    for key, value in data.items():
        if key == 'messages' and isinstance(value, list):
            # Convert messages to strings
            serialized[key] = serialize_messages(value)
        elif isinstance(value, BaseMessage):
            # Convert single message
            serialized[key] = serialize_message(value)
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            serialized[key] = make_serializable(value)
        elif isinstance(value, list):
            # Process lists
            serialized[key] = [make_serializable(item) if isinstance(item, dict) else serialize_message(item) if isinstance(item, BaseMessage) else item for item in value]
        else:
            serialized[key] = value
    
    return serialized
