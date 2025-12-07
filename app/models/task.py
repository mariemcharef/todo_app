from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.enums.state import State
from app.enums.tag import Tag

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    due_date = Column(DateTime)
    state = Column(Enum(State), nullable=False, default=State.todo)
    tag = Column(Enum(Tag), nullable=True, default=Tag.optional)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_on = Column(DateTime, default=datetime.now(timezone.utc))
    updated_on = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    user = relationship("User", lazy="joined")
