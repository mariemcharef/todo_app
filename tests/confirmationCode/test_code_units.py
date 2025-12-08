import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.routers.confirmationCode import (
    get_confirmation_code,
    confirm_account,
    disable_confirmation_code,
    add_confirmation_code,
)
from app import models, enums, schemas


@pytest.mark.parametrize("code_value", ["abc123", "xyz789"])
def test_get_confirmation_code_success(db_session: Session, code_value):
    user = models.User(
        id=1,
        first_name="a",
        last_name="b",
        email="test@example.com",
        password="test"
    )
    db_session.add(user)
    db_session.commit()

    code = models.ConfirmationCode(
        code=code_value,
        email="test@example.com",
        status=enums.CodeStatus.Pending,
        user_id=1
    )
    db_session.add(code)
    db_session.commit()

    result = get_confirmation_code(code_value, db_session)

    assert result is not None
    assert result.code == code_value
    assert result.status == enums.CodeStatus.Pending


def test_get_confirmation_code_not_found(db_session: Session):
    result = get_confirmation_code("unknown", db_session)
    assert result is None


def test_confirm_account_success(db_session: Session):
    user = models.User(
        first_name="Mariem",
        last_name="Charef",
        email="user@example.com",
        password="hashed",
        confirmed=False
    )
    db_session.add(user)
    db_session.commit()

    response = confirm_account("user@example.com", db_session)

    db_session.refresh(user)
    assert response is None
    assert user.confirmed is True


def test_confirm_account_user_not_found(db_session: Session):
    result = confirm_account("missing@example.com", db_session)

    assert result.status == status.HTTP_404_NOT_FOUND
    assert result.message == "User with this email does not exist"


def test_disable_confirmation_code_success(db_session: Session):
    user = models.User(
        id=1,
        first_name="Mariem",
        last_name="Charef",
        email="user@example.com",
        password="hashed",
        confirmed=False
    )
    db_session.add(user)
    db_session.commit()
    
    code = models.ConfirmationCode(
        code="valid-code",
        email="test@example.com",
        status=enums.CodeStatus.Pending,
        user_id=1
    )
    db_session.add(code)
    db_session.commit()

    response = disable_confirmation_code("valid-code", db_session)
    db_session.refresh(code)
    assert response is None
    assert code.status == enums.CodeStatus.Used


def test_disable_confirmation_code_not_found(db_session: Session):
    result = disable_confirmation_code("does-not-exist", db_session)

    assert result.status == status.HTTP_404_NOT_FOUND
    assert result.message == "Confirmation code does not exist"


def test_add_confirmation_code_success(db_session: Session):
    schema_code = schemas.ConfirmationCode(
        email="test@example.com",
        code="newcode123",
        status=enums.CodeStatus.Pending,
        user_id=1
    )
    result = add_confirmation_code(schema_code, db_session)

    assert result.id is not None
    assert result.code == "newcode123"
    assert result.status == enums.CodeStatus.Pending
