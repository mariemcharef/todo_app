from datetime import datetime ,timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from ..enums import CodeStatus
from ..database import Base

class ConfirmationCode(Base):
    __tablename__ = "confirmation_codes"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    email = Column(String, nullable=False)
    code = Column(String, nullable=False)
    status = Column(Enum(CodeStatus), nullable=False)
    created_on = Column(DateTime, default = datetime.now(timezone.utc), nullable=False)
    user = relationship("User", foreign_keys=[user_id])

