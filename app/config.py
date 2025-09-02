from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres.imogugwdxgdhtiuketmc:iZh5h0dT2GGeCe6W@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
    # DATABASE_URL: str = "postgresql://postgres:bester@localhost:5432/wezzie_db"
    SECRET_KEY: str = "your_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()