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

print(settings.app_name)
print(settings.debug)
print(settings.secret_key)
print(settings.database_url)
print(settings.frontend_url)