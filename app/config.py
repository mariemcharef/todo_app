from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_min: int
    mail_username: str
    mail_password: str
    mail_from: str
    mail_server: str
    google_client_id: str
    google_client_secret: str
    allow_insecure_http: bool = False
    test_database_name: str

    frontend_url: str = "http://localhost:4200"
    backend_url: str = "https://localhost:8001"

    env: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    def get_backend_url(self):
        return self.backend_url

    def get_frontend_url(self):
        return self.frontend_url


settings = Settings()
