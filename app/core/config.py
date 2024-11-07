from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    app_title: str = 'Сервис анализа патентной активности компаний.'
    cache_ttl: int = 81600
    database_url: str
    hawk_project_token: str

    #database_cli_url: str

    class Config:
        env_file = '.env'


settings = Settings()
