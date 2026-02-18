from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    # MySQL
    mysql_host: str = Field(default="mysql")
    mysql_port: int = Field(default=3306)
    mysql_database: str = Field(default="factoryops")
    mysql_user: str = Field(default="factoryops")
    mysql_password: str = Field(default="factoryops_dev")
    database_url: str = Field(default="mysql+aiomysql://factoryops:factoryops_dev@mysql:3306/factoryops")
    
    # InfluxDB
    influxdb_url: str = Field(default="http://influxdb:8086")
    influxdb_token: str = Field(default="factoryops-dev-token")
    influxdb_org: str = Field(default="factoryops")
    influxdb_bucket: str = Field(default="factoryops")
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379/0")
    celery_broker_url: str = Field(default="redis://redis:6379/1")
    celery_result_backend: str = Field(default="redis://redis:6379/2")
    
    # MinIO
    minio_endpoint: str = Field(default="minio:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin123")
    minio_bucket: str = Field(default="factoryops")
    minio_secure: bool = Field(default=False)
    
    # MQTT
    mqtt_broker_host: str = Field(default="emqx")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_username: str = Field(default="")
    mqtt_password: str = Field(default="")
    
    # JWT
    jwt_secret_key: str = Field(default="change-this-in-production-min-32-chars")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_hours: int = Field(default=24)
    
    # App
    app_env: str = Field(default="development")
    app_url: str = Field(default="http://localhost")
    log_level: str = Field(default="INFO")
    
    # Notifications (optional)
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="noreply@factoryops.local")
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_whatsapp_from: str = Field(default="")


# Singleton instance
settings = Settings()
