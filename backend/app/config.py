from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    mongo_uri: str
    mongo_db: str = "misinfoshield"
    
    redis_url: str = "redis://redis:6379/0"
    
    kafka_bootstrap_servers: str = "kafka:29092"
    
    timescaledb_url: str = "postgresql://postgres:postgres@timescaledb:5432/misinfoshield"
    
    slack_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    jwt_secret_key: str = "supersecretkey"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()