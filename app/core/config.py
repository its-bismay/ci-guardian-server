from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/ci-guardian"
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_app_webhook_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_app_name: str = "ci-guardian"
    openrouter_api_key: str = ""
    openrouter_model: str = "cohere/north-mini-code:free"
    telegram_bot_token: str = ""
    telegram_bot_username: str = "ci_guardian_bot"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    app_name: str = "CI Guardian"
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
