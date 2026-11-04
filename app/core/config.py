from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://ruta:ruta@db:5432/rutasegura"
    # Obligatoria: HS256 requiere al menos 32 bytes (RFC 7518 §3.2)
    SECRET_KEY: str = Field(
        default="rutasegura_secret_key_maraton_2026_super_segura_32b",
        min_length=32,
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Envío automático del SOS por la API oficial de WhatsApp (Meta Cloud API).
    # Opcional: sin token y phone_number_id el SOS ofrece enlaces de WhatsApp para enviar con un toque.
    WHATSAPP_TOKEN: SecretStr = SecretStr("")
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_TEMPLATE_NAME: str = ""
    WHATSAPP_TEMPLATE_LANG: str = "es"
    WHATSAPP_API_VERSION: str = "v21.0"


settings = Settings()
