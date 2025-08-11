from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str
    debug: bool
    secret_key: str
    database_url: str
    frontend_url: str

    class Config:
        env_file = ".env"

settings = Settings()
