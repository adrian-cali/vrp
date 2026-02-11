from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # Database
    postgres_user: str = "vrp_user"
    postgres_password: str = "vrp_password"
    postgres_db: str = "vrp_db"
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str = "postgresql://vrp_user:vrp_password@db:5432/vrp_db"
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_url: str = "redis://redis:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    
    # VROOM
    vroom_url: str = "http://vroom:3000"
    
    # OSRM
    osrm_url: str = "http://osrm:5000"
    
    # Cache
    fm_location_ttl: int = 600
    
    # H3
    h3_enabled: bool = False
    h3_resolution: int = 8
    h3_min_tasks: int = 100  # Minimum tasks to trigger clustering
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
