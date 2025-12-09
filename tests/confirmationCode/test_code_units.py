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

import pytest
from fastapi import status
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app import models, enums, schemas, utils
from app.routers.auth import (
    add_reset_code,
    get_reset_password_code,
    reset_password,
    disable_reset_code,
    resetPassword,
)
from app.routers.resetCode import forgot_password


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


def test_add_reset_code_success(db_session: Session):
    result = add_reset_code("user@example.com", db_session)

    assert result.email == "user@example.com"
    assert result.status == enums.CodeStatus.Pending
    assert result.reset_code is not None
    assert isinstance(result.reset_code, str)


def test_get_reset_password_code_success(db_session: Session):
    code = models.ResetCode(
        email="a@a.com",
        reset_code="token123",
        status=enums.CodeStatus.Pending,
    )
    db_session.add(code)
    db_session.commit()

    result = get_reset_password_code("token123", db_session)

    assert result is not None
    assert result.reset_code == "token123"
    assert result.status == enums.CodeStatus.Pending


def test_get_reset_password_code_not_found(db_session: Session):
    result = get_reset_password_code("unknown", db_session)
    assert result is None


def test_reset_password_success(db_session: Session):
    user = models.User(
        first_name="Mariem",
        last_name="Charef",
        email="user@example.com",
        password="old",
        confirmed=True,
    )
    db_session.add(user)
    db_session.commit()

    new_pw = "newhashed"
    reset_password("user@example.com", new_pw, db_session)
    db_session.refresh(user)

    assert user.password == new_pw


def test_reset_password_user_not_found(db_session: Session):
    response = reset_password("missing@example.com", "hash", db_session)

    assert response.status == status.HTTP_404_NOT_FOUND
    assert response.message == "No user with this email"

def test_disable_reset_code_success(db_session: Session):
    code = models.ResetCode(
        email="u@u.com",
        reset_code="tokenXYZ",
        status=enums.CodeStatus.Pending,
    )
    db_session.add(code)
    db_session.commit()

    disable_reset_code("tokenXYZ", db_session)
    db_session.refresh(code)

    assert code.status == enums.CodeStatus.Used

def test_disable_reset_code_not_found(db_session: Session):
    result = disable_reset_code("doesNotExist", db_session)
    query = db_session.query(models.ResetCode).filter(
        models.ResetCode.reset_code == "doesNotExist"
    ).all()
    assert len(query) == 0


@pytest.mark.asyncio
async def test_forgot_password_success(db_session: Session):
    user = models.User(
        first_name="Mariem",
        last_name="C",
        email="user@example.com",
        password="hashed"
    )
    db_session.add(user)
    db_session.commit()

    input_data = schemas.ForgotPassword(email="user@example.com")

    with patch("app.routers.emailUtil.send_email", new_callable=MagicMock):
        response = await forgot_password(input_data, db_session)
    assert response.status == status.HTTP_200_OK
    assert response.message == "email sent!"


@pytest.mark.asyncio
async def test_forgot_password_user_not_found(db_session: Session):
    input_data = schemas.ForgotPassword(email="missing@example.com")

    response = await forgot_password(input_data, db_session)

    assert response.status == status.HTTP_404_NOT_FOUND
    assert response.message == "No account with this email"


def test_resetPassword_reset_code_not_found(db_session: Session):
    req = schemas.ResetPassword(
        reset_password_token="bad",
        new_password="123",
        confirm_new_password="123"
    )

    result = resetPassword(req, db_session)

    assert result.status == status.HTTP_400_BAD_REQUEST
    assert "does not exist" in result.message


def test_resetPassword_code_already_used(db_session: Session):
    code = models.ResetCode(
        email="user@example.com",
        reset_code="usedtoken",
        status=enums.CodeStatus.Used,
    )
    db_session.add(code)
    db_session.commit()

    req = schemas.ResetPassword(
        reset_password_token="usedtoken",
        new_password="a",
        confirm_new_password="a"
    )

    result = resetPassword(req, db_session)

    assert result.status == status.HTTP_400_BAD_REQUEST
    assert result.message == "Code Already used"


def test_resetPassword_passwords_do_not_match(db_session: Session):
    code = models.ResetCode(
        email="user@example.com",
        reset_code="token",
        status=enums.CodeStatus.Pending,
    )
    db_session.add(code)
    db_session.commit()

    req = schemas.ResetPassword(
        reset_password_token="token",
        new_password="123",
        confirm_new_password="456"
    )

    result = resetPassword(req, db_session)

    assert result.status == status.HTTP_400_BAD_REQUEST
    assert result.message == "Passwords do not match"


def test_resetPassword_success(db_session: Session):
    user = models.User(
        first_name="a",
        last_name="b",
        email="user@example.com",
        password="oldpw"
    )
    db_session.add(user)
    db_session.commit()

    code = models.ResetCode(
        email="user@example.com",
        reset_code="tokenOK",
        status=enums.CodeStatus.Pending,
    )
    db_session.add(code)
    db_session.commit()

    with patch("app.utils.hash_password", return_value="newhashed"):
        req = schemas.ResetPassword(
            reset_password_token="tokenOK",
            new_password="abc",
            confirm_new_password="abc"
        )

        result = resetPassword(req, db_session)

    assert result.status == status.HTTP_200_OK
    assert result.message == "Password reset successfully"

    db_session.refresh(user)
    assert user.password == "newhashed"
