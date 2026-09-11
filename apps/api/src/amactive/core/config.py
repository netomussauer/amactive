"""Configuração da aplicação (settings via variáveis de ambiente)."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_SECRET = "change-me-in-env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AMACTIVE API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://amactive:amactive@localhost:5432/amactive"

    # Origens liberadas para CORS, separadas por vírgula. O default cobre o
    # Vite dev server local (ver apps/web/vite.config.ts, porta 5173).
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str = _INSECURE_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 8

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _rejeita_segredo_padrao_fora_de_dev(self) -> "Settings":
        if self.environment != "development" and self.jwt_secret == _INSECURE_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET precisa ser definido com um valor seguro fora do ambiente "
                "de desenvolvimento (ENVIRONMENT != 'development')."
            )
        return self


settings = Settings()
