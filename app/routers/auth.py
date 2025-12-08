
import json
import uuid
from fastapi import APIRouter, Depends, status, Header, HTTPException, Request, utils
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.google import GoogleSSO
import httpx
from sqlalchemy.orm import Session

from app.error import add_error
from app.routers.user import register_user
from .resetCode import add_reset_code, send_reset_code_email, get_reset_password_code, reset_password, disable_reset_code
from .confirmationCode import get_confirmation_code, confirm_account, disable_confirmation_code
from ..database import get_db
from .. import schemas, models,oauth2, enums
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone

from ..config import settings


router = APIRouter(
    tags=['Authentication']
)

google_sso = GoogleSSO(
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    redirect_uri=f"{settings.get_backend_url()}/auth/google/callback",
    allow_insecure_http=settings.allow_insecure_http
)

@router.post('/login', response_model=schemas.Token)
def login_user(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
                models.User.email == user_credentials.username).first()

    if not user:
        return schemas.Token(
            message="Invalid Credentials",
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not user.confirmed:
        return schemas.Token(
            message="Email has not been verified yet",
            status=status.HTTP_403_FORBIDDEN
        )

    # if not utils.verify(user_credentials.password, user.password):
    #     return schemas.Token(
    #         message="Invalid Credentials",
    #         status=status.HTTP_403_FORBIDDEN
    #     )
    
    data = {
        "user": {
                "first_name": user.first_name ,
                "last_name": user.last_name,
                "id": user.id,
                "email": user.email,
            },  
    }

    access_token = oauth2.create_access_token(data=data)
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        status=status.HTTP_200_OK
    )

@router.patch('/resetPassword', response_model=schemas.ResetPasswordOut)
def resetPassword(request: schemas.ResetPassword, db: Session = Depends(get_db)):
    reset_code = get_reset_password_code(request.reset_password_token, db)
    if not reset_code:
        return schemas.ResetPasswordOut(
            message="Reset link does not exist",
            status=status.HTTP_400_BAD_REQUEST
        )

    if reset_code.status == enums.CodeStatus.Used:
        return schemas.ResetPasswordOut(
            message="Code Already used",
            status=status.HTTP_400_BAD_REQUEST
        )

    expected_created_on = datetime.now(timezone.utc) + timedelta(minutes=-settings.access_token_expire_min)
    if reset_code.created_on.replace(tzinfo=timezone.utc) < expected_created_on:
        return schemas.ResetPasswordOut(
            message="Code expired",
            status=status.HTTP_400_BAD_REQUEST
        )

    if request.new_password != request.confirm_new_password:
        return schemas.ResetPasswordOut(
            message="Passwords do not match",
            status=status.HTTP_400_BAD_REQUEST
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
            status=status.HTTP_400_BAD_REQUEST
        )

    return schemas.ResetPasswordOut(
        message="Password reset successfully",
        status=status.HTTP_200_OK
    )


@router.patch('/confirmAccount', response_model=schemas.ConfirmAccountOut)
def confirmAccount(request: schemas.ConfirmAccount, db: Session = Depends(get_db)):
    confirmation_code = get_confirmation_code(request.code, db)
    if not confirmation_code:
        return schemas.ConfirmAccountOut(
            message="Confirmation code does not exist",
            status=status.HTTP_400_BAD_REQUEST
        )

    if confirmation_code.status == enums.CodeStatus.Used:
        return schemas.ConfirmAccountOut(
            message='Account Already Confirmed',
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        confirm_account(confirmation_code.email, db)
        disable_confirmation_code(request.code, db)
        db.commit()
    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.UserOut(
            message="There is a problem, try again",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return schemas.ConfirmAccountOut(
        message="Account Confirmed",
        status=status.HTTP_200_OK
    )


@router.get('/logout', response_model=schemas.Logout)
def logout_user(db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user), token: str = Depends(oauth2.oauth2_scheme)):
    try:
        blacklisted_token = models.JWTblacklist(token=token, expired_on=datetime.now(timezone.utc))
        db.add(blacklisted_token)
        db.commit()
    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.Logout(
            message="There is a problem, try again",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return schemas.Logout(
        message="Logout successfully",
        status=status.HTTP_200_OK
    )


@router.get('/login/google')
async def google_login(request: Request):
    return await google_sso.get_login_redirect()

@router.get('/auth/google/callback')
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        user = await google_sso.verify_and_process(request)
        
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        
        if not db_user:
            registration_data = {
                "email": user.email,
                "first_name": user.first_name or "",
                "last_name": user.last_name or ""
            }

            has_pending_invitation = db.query(models.Invitation).filter(
                models.Invitation.athlete_email == user.email,
                models.Invitation.status == enums.InvitationStatus.pending
            ).first() is not None

            if has_pending_invitation:
                registration_data["has_pending_invitation"]=True
                frontend_url = f"{settings.get_frontend_url()}/register?data={json.dumps(registration_data)}"
                return RedirectResponse(url=frontend_url)
            
        
            entry=schemas.User(
                **registration_data
            )
            user = register_user(entry,True,db)
            db.commit()
            data = {
                "user": {
                    "first_name": user.first_name ,
                    "last_name": user.last_name,
                    "id": user.id,
                    "email": user.email,
                },  
            }
            
            access_token = oauth2.create_access_token(data=data)
            frontend_url = f"{settings.get_frontend_url()}/auth/callback?access_token={access_token}"
            
            return RedirectResponse(url=frontend_url)
                


        data = {
            "user": {
                "first_name": user.first_name ,
                "last_name": user.last_name,
                "id": user.id,
                "email": user.email,
            },  
        }

        access_token = oauth2.create_access_token(data=data)
        
        frontend_url = f"{settings.get_frontend_url()}/auth/callback?access_token={access_token}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(
            status=status.HTTP_400_BAD_REQUEST,
            detail="Could not verify Google login"
        )

