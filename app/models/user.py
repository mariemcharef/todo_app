from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, String, Column, DateTime, Boolean
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, nullable = False) 
    email = Column(String, nullable = False, unique = True)
    first_name = Column(String, nullable = False)
    last_name = Column(String, nullable = False)
    password = Column(String, nullable = False)
    active = Column(Boolean, nullable = False, default = True)
    confirmed = Column(Boolean, nullable = False, default = False)
    created_on = Column(DateTime, default = datetime.now(timezone.utc))
