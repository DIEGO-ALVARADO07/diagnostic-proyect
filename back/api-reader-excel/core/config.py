import os
from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def decrypt_value(encrypted_value: str) -> str:
    master_key = os.getenv("APP_MASTER_KEY")
    if not master_key:
        raise ValueError("Falta la variable de entorno APP_MASTER_KEY para descifrar la configuración.")
    
    cipher = Fernet(master_key.encode())
    return cipher.decrypt(encrypted_value.encode()).decode()


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str 
    DB_PORT: int 
    DB_NAME: str 

    # Descifra automáticamente DB_USER y DB_PASSWORD al cargar la configuración
    @field_validator("DB_USER", "DB_PASSWORD", mode="before")
    @classmethod
    def decode_secrets(cls, value: str) -> str:
        # Si el valor empieza con el prefijo estándar de Fernet, lo descifra
        if value.startswith("gAAAAAB"):
            return decrypt_value(value)
        return value

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
