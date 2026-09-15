"""Configuração da aplicação (settings via variáveis de ambiente)."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_SECRET = "change-me-in-env"
_INSECURE_CREDENCIAL_CANAL_ENCRYPTION_KEY = "change-me-in-env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AMACTIVE API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://amactive:amactive@localhost:5432/amactive"

    # Diretório onde as imagens de produto são gravadas em disco (volume
    # Docker nesta fase — ver docs/data-model.md decisão #13). Default
    # relativo (`./uploads`, relativo ao diretório de trabalho do processo
    # uvicorn) cobre o caso de rodar a API fora do Docker; ao rodar via
    # `docker compose up`, o serviço `api` sobrescreve esta variável para o
    # caminho absoluto `/app/uploads` (ver `environment:` em
    # docker-compose.yml, mesmo padrão de `DATABASE_URL` acima), que é onde
    # o volume nomeado `amactive_uploads_data` é montado.
    uploads_dir: str = "./uploads"

    # Origens liberadas para CORS, separadas por vírgula. O default cobre o
    # Vite dev server local (ver apps/web/vite.config.ts, porta 5173).
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str = _INSECURE_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 8

    # Chave simétrica usada por `pgp_sym_encrypt`/`pgp_sym_decrypt` (pgcrypto)
    # para cifrar/decifrar `credencial_canal.access_token_cifrado`/
    # `client_secret_cifrado` — ver docs/design-integracao-nuvemshop.md
    # §7.2. Mesmo padrão de `jwt_secret`: sem default seguro em produção,
    # nunca logada, sempre passada como bind parameter (nunca interpolada
    # na string SQL — ver `infrastructure/persistence/repositories.py`,
    # `SqlAlchemyCredencialCanalRepository`).
    credencial_canal_encryption_key: str = _INSECURE_CREDENCIAL_CANAL_ENCRYPTION_KEY

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
        if (
            self.environment != "development"
            and self.credencial_canal_encryption_key == _INSECURE_CREDENCIAL_CANAL_ENCRYPTION_KEY
        ):
            raise ValueError(
                "CREDENCIAL_CANAL_ENCRYPTION_KEY precisa ser definido com um valor seguro fora "
                "do ambiente de desenvolvimento (ENVIRONMENT != 'development')."
            )
        return self


settings = Settings()
