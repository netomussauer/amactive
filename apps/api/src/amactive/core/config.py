"""Configuração da aplicação (settings via variáveis de ambiente).

Scaffold mínimo — sem lógica de negócio. Implementação completa fica a
cargo do dev-expert-fullcycle.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AMACTIVE API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://amactive:amactive@localhost:5432/amactive"

    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 8


settings = Settings()
