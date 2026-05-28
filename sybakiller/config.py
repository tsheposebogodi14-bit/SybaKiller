"""Application settings loaded from environment."""

from __future__ import annotations

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    syba_env: str = Field(default="production", alias="SYBA_ENV")
    syba_log_level: str = Field(default="INFO", alias="SYBA_LOG_LEVEL")
    syba_api_host: str = Field(default="127.0.0.1", alias="SYBA_API_HOST")
    syba_api_port: int = Field(default=8000, alias="SYBA_API_PORT")

    market_data_provider: str = Field(default="binance", alias="MARKET_DATA_PROVIDER")
    market_data_symbols: str = Field(
        default="BTCUSDT,ETHUSDT",
        alias="MARKET_DATA_SYMBOLS",
    )

    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", alias="BINANCE_API_SECRET")
    binance_testnet: bool = Field(default=False, alias="BINANCE_TESTNET")

    syba_tenant_id: str = Field(default="default", alias="SYBA_TENANT_ID")

    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    redis_ticks_enabled: bool = Field(default=True, alias="REDIS_TICKS_ENABLED")

    state_snapshot_enabled: bool = Field(default=True, alias="STATE_SNAPSHOT_ENABLED")
    state_snapshot_interval_sec: float = Field(default=30.0, alias="STATE_SNAPSHOT_INTERVAL_SEC")

    database_url: str = Field(
        default="postgresql+asyncpg://syba:syba@127.0.0.1:5432/sybakiller",
        alias="DATABASE_URL",
    )

    syba_max_order_notional: float = Field(default=100_000.0, alias="SYBA_MAX_ORDER_NOTIONAL")
    syba_max_position_notional: float = Field(default=500_000.0, alias="SYBA_MAX_POSITION_NOTIONAL")
    syba_max_orders_per_second: float = Field(default=50.0, alias="SYBA_MAX_ORDERS_PER_SECOND")

    @property
    def market_data_symbols_list(self) -> list[str]:
        return [s.strip().upper() for s in self.market_data_symbols.split(",") if s.strip()]

    @field_validator("market_data_provider")
    @classmethod
    def _provider_not_simulated_in_prod(cls, value: str, info: ValidationInfo) -> str:
        env = (info.data.get("syba_env") or "production").lower()
        if env == "production" and value.lower() == "simulated":
            raise ValueError("simulated feed is not allowed when SYBA_ENV=production")
        return value


def get_settings() -> Settings:
    return Settings()
