from typing import  Optional, List
from datetime import datetime
from app.enums.codeStatus import CodeStatus
from pydantic import BaseModel, EmailStr, ConfigDict

from app.enums.state import State
from app.enums.tag import Tag
class OurBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
        

class OurBaseModelOut(OurBaseModel):
    message: Optional[str] = None
    status: Optional[int] = None

class PagedResponse(OurBaseModelOut):
    page_number: Optional[int] = None
    page_size: Optional[int] = None
    total_pages: Optional[int] = None
    total_records: Optional[int] = None


class User(OurBaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    confirm_password: str

class EditUser(OurBaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None

class UserOut(OurBaseModelOut):
    id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    confirmed: Optional[bool] = None
    created_on: Optional[datetime] = None
    new_token: Optional[str] =None

class UsersOut(PagedResponse):
    list: Optional[List[UserOut]] = None

class Token(OurBaseModelOut):
    access_token: Optional[str] = None
    token_type: Optional[str] = None

class TokenData(OurBaseModel):
    id: Optional[int] = None

class ResetCode(OurBaseModel):
    email: EmailStr
    reset_code: str
    status: CodeStatus

class ResetCodeDeactivate(OurBaseModel):
    status: CodeStatus

class ForgotPassword(OurBaseModel):
    email: EmailStr

class ForgotPasswordOut(OurBaseModelOut):
    pass

class ResetPassword(OurBaseModel):
    reset_password_token: str
    new_password: str
    confirm_new_password: str

class ResetPasswordOut(OurBaseModelOut):
    pass

class UserResetPassword(OurBaseModel):
    email: EmailStr
    password: str

class SendConfirmationEmail(OurBaseModel):
    email: EmailStr

class ConfirmAccount(OurBaseModel):
    code: str

class ConfirmAccountOut(OurBaseModelOut):
    pass

class ConfirmationCode(OurBaseModel):
    email: EmailStr
    code: str
    status: CodeStatus

class UserConfirm(OurBaseModel):
    confirmed: bool

class TagOut(OurBaseModelOut):
    id: Optional[int] = None
    name: Optional[str] = None
    color: Optional[str] = None
    created_on: Optional[datetime] = None

class ErrorOut(OurBaseModelOut):
    id: Optional[int] = None
    orig: Optional[str] = None
    statement: Optional[str] = None
    params: Optional[str] = None
    created_on: Optional[datetime] = None

class taskIn(OurBaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    tag: Optional[Tag] = None

class taskOut(OurBaseModelOut):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    tag: Optional[Tag] = None
    state: Optional[State] = None
    user_id: Optional[int] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    
class tasksOut(PagedResponse):
    list: Optional[List[taskOut]] = None

class Logout(OurBaseModelOut):
    pass

class Code(OurBaseModel):
    email: EmailStr
    code: str
    status: CodeStatus
    user_id: int


class CodeDeactivate(OurBaseModel):
    status: CodeStatus
