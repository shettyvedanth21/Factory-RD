"""
Analytics worker tasks.
Implements anomaly detection, failure prediction, and energy forecasting using ML models.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from prophet import Prophet

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.core.minio_client import upload_json
from app.models.analytics_job import AnalyticsJob, JobStatus
from app.services.telemetry_fetcher import fetch_as_dataframe
from sqlalchemy import select, update


logger = get_logger(__name__)


def run_anomaly_detection(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run anomaly detection using Isolation Forest.
    
    Args:
        df: DataFrame with telemetry data
    
    Returns:
        Dictionary with anomaly detection results
    """
    if df.empty or len(df) < 10:
        return {
            "error": "Insufficient data for anomaly detection",
            "required_rows": 10,
            "actual_rows": len(df),
        }
    
    # Get numeric columns (excluding timestamp and device_id)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in ["device_id"]]
    
    if not feature_cols:
        return {"error": "No numeric features available for anomaly detection"}
    
    # Prepare feature matrix, fill NaN with median
    X = df[feature_cols].fillna(df[feature_cols].median())
    
    # Train Isolation Forest
    model = IsolationForest(
        contamination=0.05,  # Expect 5% anomalies
        random_state=42,
        n_estimators=100,
    )
    
    scores = model.fit_predict(X)
    anomaly_mask = scores == -1
    
    # Extract anomalies with details
    anomalies = []
    for idx in df[anomaly_mask].index:
        row = df.iloc[idx]
        
        # Calculate anomaly score (negative of decision function)
        anomaly_score = float(abs(model.score_samples([X.iloc[idx]])[0]))
        
        anomalies.append({
            "device_id": int(row.get("device_id", 0)),
            "timestamp": row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None,
            "score": anomaly_score,
            "affected_parameters": feature_cols,
        })
    
    # Sort by score and limit to top 50
    anomalies_sorted = sorted(anomalies, key=lambda x: x["score"], reverse=True)[:50]
    
    return {
        "anomaly_count": int(anomaly_mask.sum()),
        "anomaly_score": float(anomaly_mask.mean()),
        "total_data_points": len(df),
        "anomalies": anomalies_sorted,
        "summary": f"{int(anomaly_mask.sum())} anomalies detected in {len(df)} data points",
        "features_analyzed": feature_cols,
    }


def run_energy_forecast(df: pd.DataFrame, horizon_days: int = 7) -> Dict[str, Any]:
    """
    Run energy consumption forecast using Prophet.
    
    Args:
        df: DataFrame with telemetry data
        horizon_days: Number of days to forecast
    
    Returns:
        Dictionary with forecast results
    """
    if "power" not in df.columns:
        return {"error": "No power parameter available for forecasting"}
    
    # Prepare time series data
    ts_df = df[["timestamp", "power"]].dropna()
    
    if len(ts_df) < 24:
        return {
            "error": "Insufficient data for forecasting",
            "required_rows": 24,
            "actual_rows": len(ts_df),
        }
    
    # Rename columns for Prophet
    ts_df = ts_df.copy()
    ts_df.columns = ["ds", "y"]
    
    # Ensure timezone-naive datetime
    ts_df["ds"] = pd.to_datetime(ts_df["ds"]).dt.tz_localize(None)
    
    # Train Prophet model
    model = Prophet(
        daily_seasonality=True,
        yearly_seasonality=False,
        weekly_seasonality=True,
    )
    
    try:
        model.fit(ts_df)
    except Exception as e:
        logger.error("prophet.fit_failed", error=str(e))
        return {"error": f"Prophet model fitting failed: {str(e)}"}
    
    # Generate future dataframe (hourly intervals)
    future = model.make_future_dataframe(periods=horizon_days * 24, freq="H")
    forecast = model.predict(future)
    
    # Extract only future predictions
    future_only = forecast[forecast["ds"] > ts_df["ds"].max()]
    
    # Convert to serializable format
    forecast_data = []
    for _, row in future_only.iterrows():
        forecast_data.append({
            "timestamp": row["ds"].isoformat(),
            "yhat": float(row["yhat"]),
            "yhat_lower": float(row["yhat_lower"]),
            "yhat_upper": float(row["yhat_upper"]),
        })
    
    return {
        "horizon_days": horizon_days,
        "forecast_points": len(forecast_data),
        "forecast": forecast_data,
        "summary": f"Energy forecast for next {horizon_days} days generated ({len(forecast_data)} hourly predictions)",
        "historical_points": len(ts_df),
    }


def run_failure_prediction(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run failure prediction using rolling statistics and anomaly detection.
    
    Args:
        df: DataFrame with telemetry data
    
    Returns:
        Dictionary with failure prediction results
    """
    if df.empty or len(df) < 20:
        return {
            "error": "Insufficient data for failure prediction",
            "required_rows": 20,
            "actual_rows": len(df),
        }
    
    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in ["device_id"]]
    
    if not feature_cols:
        return {"error": "No numeric features available for failure prediction"}
    
    # Prepare feature matrix
    X = df[feature_cols].fillna(df[feature_cols].median())
    
    # Feature engineering: rolling statistics as anomaly proxy
    X_feat = pd.DataFrame()
    for col in feature_cols:
        X_feat[f"{col}_mean"] = X[col].rolling(10, min_periods=1).mean()
        X_feat[f"{col}_std"] = X[col].rolling(10, min_periods=1).std().fillna(0)
    
    # Use Isolation Forest as proxy for failure risk
    model = IsolationForest(contamination=0.1, random_state=42)
    scores = model.fit_predict(X_feat)
    
    failure_prob = float((scores == -1).mean())
    
    # Categorize risk level
    if failure_prob < 0.1:
        risk_level = "low"
    elif failure_prob < 0.25:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    return {
        "failure_probability": round(failure_prob, 4),
        "risk_level": risk_level,
        "summary": f"Failure risk assessed as {risk_level} ({failure_prob*100:.1f}%)",
        "total_data_points": len(df),
        "features_analyzed": feature_cols,
    }


def run_ai_copilot(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run AI Copilot mode - combines multiple analytics.
    
    Args:
        df: DataFrame with telemetry data
    
    Returns:
        Dictionary with combined results from all models
    """
    results = {}
    
    # Run anomaly detection if enough data
    if not df.empty and len(df) >= 10:
        results["anomaly"] = run_anomaly_detection(df)
    
    # Run energy forecast if power data available
    if "power" in df.columns and len(df) >= 24:
        results["forecast"] = run_energy_forecast(df)
    
    # Always run failure prediction
    results["failure"] = run_failure_prediction(df)
    
    # Combine summaries
    summary_parts = [r.get("summary", "") for r in results.values() if "summary" in r]
    
    return {
        "mode": "ai_copilot",
        "models_used": list(results.keys()),
        "results": results,
        "summary": " | ".join(summary_parts),
    }


# Synchronous helper functions for Celery tasks
def get_job_sync(job_id: str) -> AnalyticsJob:
    """Get job from database synchronously."""
    import asyncio
    from app.core.database import AsyncSessionLocal
    
    async def _get():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AnalyticsJob).where(AnalyticsJob.id == job_id)
            )
            return result.scalar_one()
    
    return asyncio.run(_get())


def update_job_status_sync(
    job_id: str,
    status: str,
    result_url: str = None,
    error: str = None,
    results: Dict[str, Any] = None,
) -> None:
    """Update job status synchronously."""
    import asyncio
    from app.core.database import AsyncSessionLocal
    
    async def _update():
        async with AsyncSessionLocal() as db:
            update_data = {"status": JobStatus[status.upper()]}
            
            if status == "running":
                update_data["started_at"] = datetime.utcnow()
            elif status in ["complete", "failed"]:
                update_data["completed_at"] = datetime.utcnow()
            
            if result_url:
                update_data["result_url"] = result_url
            
            if error:
                update_data["error_message"] = error
            
            await db.execute(
                update(AnalyticsJob)
                .where(AnalyticsJob.id == job_id)
                .values(**update_data)
            )
            await db.commit()
    
    asyncio.run(_update())


@celery_app.task(name="run_analytics_job", bind=True, max_retries=1, queue="analytics")
def run_analytics_job(self, job_id: str):
    """
    Run analytics job asynchronously.
    
    Args:
        job_id: Analytics job ID
    """
    logger.info("analytics_job.start", job_id=job_id)
    
    # Update status to running
    update_job_status_sync(job_id, "running")
    
    try:
        # Fetch job details
        job = get_job_sync(job_id)
        
        logger.info(
            "analytics_job.fetching_data",
            job_id=job_id,
            factory_id=job.factory_id,
            job_type=job.job_type.value,
            device_count=len(job.device_ids),
        )
        
        # Fetch telemetry data
        df = asyncio.run(
            fetch_as_dataframe(
                job.factory_id,
                job.device_ids,
                job.date_range_start,
                job.date_range_end,
            )
        )
        
        logger.info(
            "analytics_job.data_fetched",
            job_id=job_id,
            rows=len(df),
            columns=len(df.columns) if not df.empty else 0,
        )
        
        # Dispatch to appropriate analytics function
        dispatch = {
            "anomaly": run_anomaly_detection,
            "failure_prediction": run_failure_prediction,
            "energy_forecast": run_energy_forecast,
            "ai_copilot": run_ai_copilot,
        }
        
        fn = dispatch.get(job.job_type.value)
        if not fn:
            raise ValueError(f"Unknown job type: {job.job_type.value}")
        
        # Run analytics
        results = fn(df)
        
        logger.info(
            "analytics_job.analysis_complete",
            job_id=job_id,
            job_type=job.job_type.value,
        )
        
        # Upload results to MinIO
        result_url = upload_json(job.factory_id, job_id, results)
        
        # Update job status
        update_job_status_sync(job_id, "complete", result_url=result_url)
        
        logger.info(
            "analytics_job.success",
            job_id=job_id,
            result_url=result_url,
        )
        
        return {"status": "complete", "result_url": result_url}
        
    except Exception as e:
        logger.error(
            "analytics_job.failed",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        
        # Update job status to failed
        update_job_status_sync(job_id, "failed", error=str(e))
        
        # Retry if possible
        raise self.retry(exc=e)
