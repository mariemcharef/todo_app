from datetime import datetime ,timezone
from sqlalchemy import Column, Integer, DateTime, String
from ..database import Base

class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key = True, nullable = False)
    error = Column(String, nullable = False)
    created_on = Column(DateTime, default = datetime.now(timezone.utc))
