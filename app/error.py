from fastapi import Depends, status
from . import models, schemas
from .database import get_db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

def add_error(e: SQLAlchemyError, db: Session = Depends(get_db)):
    error = models.Error(
        error=str(e)
    )
    try:
        db.add(error)
        db.commit()
        db.refresh(error)
    except Exception as e:
        db.rollback()
        return schemas.ErrorOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="something went wrong"
        )
    return schemas.ErrorOut(**error.__dict__,
        status=status.HTTP_201_CREATED,
        message="error added successfully"
    )

def get_error_message(error_message, error_keys):
    for error_key in error_keys:
        if error_key in error_message:
            return error_keys[error_key]

    return "Something went wrong"
