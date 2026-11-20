import os
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Ruta absoluta del archivo .env ubicado junto a config.py
ENV_FILE = Path(__file__).resolve().parent / ".env"


def decrypt_value(encrypted_value: str, master_key: str | None) -> str:
    if not master_key:
        raise ValueError(
            "Falta APP_MASTER_KEY para descifrar la configuración."
        )

    cipher = Fernet(master_key.encode())
    return cipher.decrypt(encrypted_value.encode()).decode()


class Settings(BaseSettings):

    # Se declara primero para que esté disponible en los validadores.
    # No se incluye en la representación ni en model_dump().
    APP_MASTER_KEY: str | None = Field(
        default=None,
        repr=False,
        exclude=True
    )

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # Descifrado automático de las credenciales
    @field_validator("DB_USER", "DB_PASSWORD", mode="before")
    @classmethod
    def decode_secrets(cls, value: str, info: ValidationInfo) -> str:

        if isinstance(value, str) and value.startswith("gAAAAAB"):
            master_key = (
                info.data.get("APP_MASTER_KEY")
                or os.getenv("APP_MASTER_KEY")
            )

            return decrypt_value(value, master_key)

        return value

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
