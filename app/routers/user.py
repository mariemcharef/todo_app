from operator import and_
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import utils

from .confirmationCode import add_confirmation_code
from ..database import get_db
from .. import schemas, models, enums, oauth2
from sqlalchemy import func
from .emailUtil import send_email
from typing import Optional
from datetime import datetime, timedelta, timezone
import uuid

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

error_keys = {
    'positive_height': 'height should be positive > 0',
}


async def sendConfirmationMail(email: str, user_id: int, db: any):
    confirmation_code = schemas.Code(
        email=email,
        code=str(uuid.uuid1()),
        status=enums.CodeStatus.Pending,
        user_id=user_id
    )

    add_confirmation_code(confirmation_code, db)

    subject = "Account Confirmation"
    recipients = [email]

    await send_email(
        subject=subject,
        recipients=recipients,
        email_template=enums.EmailTemplate.ConfirmAccount,
        email=email,
        code=confirmation_code.code
    )
    

def register_user(entry: schemas.User,confirm_account:bool, db:Session=Depends(get_db)):
    if not entry.password:
        entry.password=str(uuid.uuid1()) 

    entry.password = utils.hash_password(entry.password)
    user = entry.model_dump()
    user.pop('confirm_password')

    user = models.User(**user)
    user.confirmed=confirm_account
    db.add(user)
    db.flush()
    return user

@router.post('/', response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(entry: schemas.User, db: Session = Depends(get_db)):
    user_in_db = db.query(models.User).filter(models.User.email == entry.email).first()
    if user_in_db:
        return schemas.UserOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Email already used"
        )

    if entry.password != entry.confirm_password:
        return schemas.UserOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Passwords must match!"
        )

    try:
        registeration_result=register_user(entry,False,db)
        if isinstance( registeration_result, schemas.ErrorOut):
            return registeration_result
        
        user = registeration_result
        
        await sendConfirmationMail(user.email, user.id, db) 
        db.commit()
    except Exception as e:
        print(e)
        db.rollback()
        return schemas.UserOut(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message='error',
        )

    return schemas.UserOut(**user.__dict__,
        status=status.HTTP_201_CREATED,
        message="User created successfully and a confirmation email sent."
    )

@router.post('/registerWithGoogle', response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_with_google(entry: schemas.User, db: Session = Depends(get_db)):
    try:
        user=register_user(entry,True,db)
        db.commit()
        data = {
            "user": {
                "first_name": user.first_name ,
                "last_name": user.last_name,
                "id": user.id,
                "email": user.email,
            },  
        }
        new_token = oauth2.create_access_token(data=data)
    except Exception as e:
        print(e)
        db.rollback()
       
        return schemas.UserOut(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message='error',
        )

    return schemas.UserOut(**user.__dict__,
        new_token=new_token,
        status=status.HTTP_201_CREATED,
        message="User created successfully"
    )

def get_user_data(user_id: int, db: Session):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        return schemas.UserOut(
            message=f"User with id: {id} does not exist",
            status=status.HTTP_404_NOT_FOUND
        )
    
    return schemas.UserOut(
        **user.__dict__,
        message=f"User with id {user_id}",
        status=status.HTTP_200_OK
    )

@router.get('/{id}', response_model=schemas.UserOut, status_code=status.HTTP_200_OK)
def get_user_by_id(id: int, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    return get_user_data(id, db)

@router.get('/me/', response_model=schemas.UserOut)
def get_current_user(db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    return get_user_data(current_user.id, db)

@router.get('/', response_model=schemas.UsersOut)
def get_users(db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user), page_size: int = 10, page_number: int = 1, name_substr: Optional[str] = None):
    query = db.query(models.User)
    if name_substr:
        query = query.filter(
            func.CONCAT(models.User.first_name, " ", models.User.last_name).contains(name_substr))

    total_records = query.count()
    total_pages = utils.div_ceil(total_records, page_size)
    users = query.limit(page_size).offset((page_number-1)*page_size).all()
    return schemas.UsersOut(
        total_pages=total_pages,
        total_records=total_records,
        page_number=page_number,
        page_size=page_size,
        list=[schemas.UserOut(**user.__dict__) for user in users],
        message="All users",
        status=status.HTTP_200_OK
    )


@router.put('/{id}', response_model=schemas.UserOut, status_code=status.HTTP_200_OK)
def update_user(id: int, user: schemas.EditUser, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    if current_user.id != id:
        return schemas.UserOut(
            status=status.HTTP_401_UNAUTHORIZED,
            message="You are not authorized to update this user"
        )
    user_to_update = db.query(models.User).filter(models.User.id == id)
    db_user = user_to_update.first()
    if not db_user:
        return schemas.UserOut(
            status=status.HTTP_404_NOT_FOUND,
            message="User does not exist"
        )
    try:     
        user_fields = user.model_dump(exclude_unset=True)
        user_fields.pop('email',None)
        user_to_update.update(user_fields)
        db.commit()
        db.refresh(db_user)
        data = {
            "user": {
                "first_name": user.first_name ,
                "last_name": user.last_name,
                "id": current_user.id,
                "email": user.email,
            },  
        }
        new_token = oauth2.create_access_token(data=data)
    except Exception as e:
        db.rollback()
        return schemas.UserOut(
            status=status.HTTP_400_BAD_REQUEST,
            message='error'
        )
    return schemas.UserOut(
        status=status.HTTP_200_OK,
        message="User updated successfully",
        new_token= new_token
    )
