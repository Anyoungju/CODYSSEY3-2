"""Pydantic request and response contracts."""
from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field


class DataInput(BaseModel):
    date: date
    value: float = Field(ge=-1000000, le=1000000)
    memo: str = Field(default="", max_length=300)


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None


class ConversationInput(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    messages: list[dict] = Field(default_factory=list)
