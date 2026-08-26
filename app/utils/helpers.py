"""Shared utility functions."""

import uuid
from datetime import datetime


def generate_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()
