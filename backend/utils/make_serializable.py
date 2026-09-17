import json
from typing import Any
from langchain_core.messages import BaseMessage

def make_serializable(obj: Any) -> Any:
    """Recursively convert any object into something JSON-serializable."""
    if isinstance(obj, BaseMessage):
        return {
            "type": obj.__class__.__name__,
            "content": obj.content,
            "additional_kwargs": getattr(obj, "additional_kwargs", {}),
            "id": getattr(obj, "id", None),
        }
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)