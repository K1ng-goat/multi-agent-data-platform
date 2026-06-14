"""User preference model — simple key-value store for global settings."""
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=0)
    key = Column(String(255), nullable=False)
    value = Column(Text)
