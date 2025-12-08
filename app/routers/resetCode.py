from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import utils
from app.config import Settings
from app.error import add_error
from app.routers.confirmationCode import confirm_account, disable_confirmation_code, get_confirmation_code
from ..database import get_db 
from .. import schemas, models, enums
import uuid
from ..routers.emailUtil import send_email

router = APIRouter(
    tags=['Authentication']
)


async def send_reset_code_email(email: str, reset_code: str):
    subject = "Reset Password"
    recipients = [email]
    await send_email(subject, recipients, enums.EmailTemplate.ResetPassword, email, reset_code)

def add_reset_code(email: str, db: Session = Depends(get_db)):
    reset_code = models.ResetCode(
        email = email,
        reset_code = str(uuid.uuid1()),
        status = enums.CodeStatus.Pending
    )
    db.add(reset_code)
    db.flush()
    return reset_code

def get_reset_password_code(reset_code: str, db: Session = Depends(get_db)):
    return db.query(models.ResetCode).filter(models.ResetCode.reset_code == reset_code).first()

def reset_password(email: str, new_hashed_password: str, db: Session = Depends(get_db)):
    user_query = db.query(models.User).filter(models.User.email == email)
    user = user_query.first()
    if not user: 
        return schemas.ResetPasswordOut(
            message = "No user with this email",
            status = status.HTTP_404_NOT_FOUND
        )
    fields_to_update = schemas.UserResetPassword(
        email = user.email,
        password = new_hashed_password
    )
    user_query.update(fields_to_update.model_dump(), synchronize_session=False)

def disable_reset_code(reset_code: str, db: Session = Depends(get_db)):
    reset_code_query = db.query(models.ResetCode).filter(models.ResetCode.reset_code == reset_code)
    fields_to_update = schemas.ResetCodeDeactivate(status=enums.CodeStatus.Used)
    reset_code_query.update(fields_to_update.model_dump(), synchronize_session = False)

   
@router.post('/forgotPassword', response_model=schemas.ForgotPasswordOut)
async def forgot_password(input: schemas.ForgotPassword, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == input.email).first()
    if not user:
        return schemas.ForgotPasswordOut(
            message="No account with this email",
            status=status.HTTP_404_NOT_FOUND
        )
    try:
        reset_code = add_reset_code(input.email, db)
        db.flush()
        await send_reset_code_email(input.email, reset_code.reset_code)
        db.commit()
    except Exception as e:
        db.rollback()
        add_error(e,db)
        return schemas.ForgotPasswordOut(
            message="Something went wrong",
            status=status.HTTP_400_BAD_REQUEST
        )

    return schemas.ForgotPasswordOut(
        message="email sent!",
        status=status.HTTP_200_OK
    )

@router.patch('/resetPassword', response_model=schemas.ResetPasswordOut)
def resetPassword(request: schemas.ResetPassword, db: Session = Depends(get_db)):
    reset_code = get_reset_password_code(request.reset_password_token, db)
    if not reset_code:
        return schemas.ResetPasswordOut(
            message="Reset link does not exist",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if reset_code.status == enums.CodeStatus.used:
        return schemas.ResetPasswordOut(
            message="Code Already used",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    expected_created_on = datetime.now(timezone.utc) + timedelta(minutes=-Settings.access_token_expire_min)
    if reset_code.created_on.replace(tzinfo=timezone.utc) < expected_created_on:
        return schemas.ResetPasswordOut(
            message="Code expired",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if request.new_password != request.confirm_new_password:
        return schemas.ResetPasswordOut(
            message="Passwords do not match",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    try:
        new_hashed_password = utils.hash_password(request.new_password)
        reset_password(reset_code.email, new_hashed_password, db)
        disable_reset_code(request.reset_password_token, db)
        db.commit()
    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.ResetPasswordOut(
            message="Something went wrong!",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return schemas.ResetPasswordOut(
        message="Password reset successfully",
        status_code=status.HTTP_200_OK
    )


@router.patch('/confirmAccount', response_model=schemas.ConfirmAccountOut)
def confirmAccount(request: schemas.ConfirmAccount, db: Session = Depends(get_db)):
    code = get_confirmation_code(request.code, db)
    if not code:
        return schemas.ConfirmAccountOut(
            message="Confirmation code does not exist",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if code.status == enums.CodeStatus.used:
        return schemas.ConfirmAccountOut(
            message='Account Already Confirmed',
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    if request.user_id is not None:
        if request.user_id != code.user_id:
            return schemas.ConfirmAccountOut(
                message='You cannot confirn another user account',
                status_code=status.HTTP_403_FORBIDDEN
            )
    try:
        confirm_account(code.email, db)
        disable_confirmation_code(request.code, db)
        db.commit()
    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.UserOut(
            message="There is a problem, try again",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return schemas.ConfirmAccountOut(
        message="Account Confirmed",
        status_code=status.HTTP_200_OK
    )

