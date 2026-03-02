from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG_TURN_TRACE: bool = False

settings = Settings()
