"""
MinIO client for object storage.
Used for storing analytics results and generated reports.
"""
import json
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


# Initialize S3 client for MinIO
s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{settings.minio_endpoint}",
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


async def ensure_bucket_exists() -> None:
    """
    Ensure the MinIO bucket exists, create if not.
    Called during application startup.
    """
    try:
        s3_client.head_bucket(Bucket=settings.minio_bucket)
        logger.info("minio.bucket_exists", bucket=settings.minio_bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            # Bucket doesn't exist, create it
            try:
                s3_client.create_bucket(Bucket=settings.minio_bucket)
                logger.info("minio.bucket_created", bucket=settings.minio_bucket)
            except ClientError as create_error:
                logger.error(
                    "minio.bucket_create_failed",
                    bucket=settings.minio_bucket,
                    error=str(create_error),
                )
                raise
        else:
            logger.error(
                "minio.bucket_check_failed",
                bucket=settings.minio_bucket,
                error=str(e),
            )
            raise


def upload_json(factory_id: int, job_id: str, data: dict) -> str:
    """
    Upload JSON data to MinIO and return presigned URL.
    
    Args:
        factory_id: Factory ID for path namespacing
        job_id: Job ID for filename
        data: Dictionary to serialize as JSON
    
    Returns:
        Presigned URL valid for 1 hour
    """
    key = f"{factory_id}/analytics/{job_id}.json"
    
    try:
        s3_client.put_object(
            Bucket=settings.minio_bucket,
            Key=key,
            Body=json.dumps(data, indent=2, default=str),
            ContentType="application/json",
        )
        logger.info(
            "minio.upload_success",
            factory_id=factory_id,
            job_id=job_id,
            key=key,
        )
        
        # Generate presigned URL
        url = generate_presigned_url(key, expiry=3600)
        return url
        
    except ClientError as e:
        logger.error(
            "minio.upload_failed",
            factory_id=factory_id,
            job_id=job_id,
            key=key,
            error=str(e),
        )
        raise


def upload_report(factory_id: int, report_id: str, file_data: bytes, file_format: str) -> str:
    """
    Upload report file to MinIO and return presigned URL.
    
    Args:
        factory_id: Factory ID for path namespacing
        report_id: Report ID for filename
        file_data: Binary file data
        file_format: File format (pdf, excel, json)
    
    Returns:
        Presigned URL valid for 24 hours
    """
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }
    
    extensions = {
        "pdf": "pdf",
        "excel": "xlsx",
        "json": "json",
    }
    
    ext = extensions.get(file_format, "bin")
    key = f"{factory_id}/reports/{report_id}.{ext}"
    content_type = content_types.get(file_format, "application/octet-stream")
    
    try:
        s3_client.put_object(
            Bucket=settings.minio_bucket,
            Key=key,
            Body=file_data,
            ContentType=content_type,
        )
        logger.info(
            "minio.report_upload_success",
            factory_id=factory_id,
            report_id=report_id,
            key=key,
            size_bytes=len(file_data),
        )
        
        # Generate presigned URL valid for 24 hours
        url = generate_presigned_url(key, expiry=86400)
        return url
        
    except ClientError as e:
        logger.error(
            "minio.report_upload_failed",
            factory_id=factory_id,
            report_id=report_id,
            key=key,
            error=str(e),
        )
        raise


def generate_presigned_url(key: str, expiry: int = 3600) -> str:
    """
    Generate a presigned URL for downloading an object.
    
    Args:
        key: Object key in MinIO
        expiry: URL expiry in seconds (default 1 hour)
    
    Returns:
        Presigned URL
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.minio_bucket,
                "Key": key,
            },
            ExpiresIn=expiry,
        )
        return url
    except ClientError as e:
        logger.error(
            "minio.presigned_url_failed",
            key=key,
            error=str(e),
        )
        raise


def check_minio_health() -> bool:
    """
    Check if MinIO is accessible.
    
    Returns:
        True if accessible, False otherwise
    """
    try:
        s3_client.head_bucket(Bucket=settings.minio_bucket)
        return True
    except Exception as e:
        logger.warning("minio.health_check_failed", error=str(e))
        return False
