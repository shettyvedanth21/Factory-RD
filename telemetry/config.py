from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Telemetry service settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    # MySQL
    database_url: str = Field(default="mysql+aiomysql://factoryops:factoryops_dev@mysql:3306/factoryops")
    
    # InfluxDB
    influxdb_url: str = Field(default="http://influxdb:8086")
    influxdb_token: str = Field(default="factoryops-dev-token")
    influxdb_org: str = Field(default="factoryops")
    influxdb_bucket: str = Field(default="factoryops")
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379/0")
    celery_broker_url: str = Field(default="redis://redis:6379/1")
    
    # MQTT
    mqtt_broker_host: str = Field(default="emqx")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_username: str = Field(default="")
    mqtt_password: str = Field(default="")
    
    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")


# Singleton instance
settings = Settings()
