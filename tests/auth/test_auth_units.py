
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
from app.enums.codeStatus import CodeStatus
from app.routers import auth
from app import models, schemas
from unittest.mock import AsyncMock

class DummyUser:
    def __init__(self, email, confirmed=True):
        self.id = 1
        self.email = email
        self.first_name = "John"
        self.last_name = "Doe"
        self.confirmed = confirmed
        self.password = "hashedpass"


@pytest.mark.asyncio
async def test_login_invalid_email():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    creds = MagicMock()
    creds.username = "wrong@mail.com"
    creds.password = "123"

    result = auth.login_user(creds, mock_db)

    assert result.status == status.HTTP_403_FORBIDDEN
    assert result.message == "Invalid Credentials"


@pytest.mark.asyncio
async def test_login_not_confirmed():
    user = DummyUser("test@mail.com", confirmed=False)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = user

    creds = MagicMock()
    creds.username = "test@mail.com"
    creds.password = "123"

    result = auth.login_user(creds, mock_db)

    assert result.status == status.HTTP_403_FORBIDDEN
    assert "not been verified" in result.message


@pytest.mark.asyncio
async def test_login_success():
    user = DummyUser("test@mail.com", confirmed=True)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = user

    creds = MagicMock()
    creds.username = "test@mail.com"
    creds.password = "123"

    with patch("app.routers.auth.oauth2.create_access_token", return_value="jwt123"):
        result = auth.login_user(creds, mock_db)

    assert result.status == status.HTTP_200_OK
    assert result.access_token == "jwt123"


@pytest.mark.asyncio
def test_forgot_password_email_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    req = schemas.ForgotPassword(email="none@mail.com")

    result =  auth.resetPassword(req, mock_db)
    print(result)
    assert result.status == status.HTTP_404_NOT_FOUND
    assert "No account" in result.message

def test_reset_password_code_not_found():
    mock_db = MagicMock()    
    auth.get_reset_password_code = MagicMock(return_value=None)
    req = schemas.ResetPassword(
        email='test@yopmail.com',
        reset_code= "wrong_token",
        status= CodeStatus.Pending

    )

    result = auth.resetPassword(req, mock_db)

    assert result.status == status.HTTP_400_BAD_REQUEST
    assert "Reset link does not exist" in result.message

def test_reset_password_code_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    req = schemas.ResetPassword(reset_password_token="bad", new_password="a", confirm_new_password="a")

    result = auth.resetPassword(req, mock_db)

    assert result.status == status.HTTP_400_BAD_REQUEST
    assert "does not exist" in result.message


def test_reset_password_mismatch():
    reset_code = MagicMock()
    reset_code.status = CodeStatus.Pending
    reset_code.created_on = datetime.now(timezone.utc)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = reset_code

    req = schemas.ResetPassword(
        reset_password_token="123",
        new_password="abc",
        confirm_new_password="xyz"
    )

    result = auth.resetPassword(req, mock_db)
    assert result.status == status.HTTP_400_BAD_REQUEST
    assert "match" in result.message

def test_confirm_account_invalid_code():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    req = schemas.ConfirmAccount(confirmation_code="bad", user_id=1)

    result = auth.confirmAccount(req, mock_db)

    assert result.status == status.HTTP_400_BAD_REQUEST
    assert "does not exist" in result.message
