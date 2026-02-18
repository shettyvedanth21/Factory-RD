from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models import User
from app.schemas.parameter import ParameterResponse, ParameterUpdate
from app.schemas.kpi import KPILiveResponse, KPIHistoryResponse
from app.repositories import device_repo, parameter_repo
from app.services import kpi_service


router = APIRouter(tags=["Telemetry"])
logger = get_logger(__name__)


@router.get("/devices/{device_id}/parameters", response_model=dict)
async def list_device_parameters(
    device_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all parameters for a device.
    
    Returns 404 if device not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    # Verify device exists and belongs to factory
    device = await device_repo.get_by_id(db, factory_id, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get parameters
    parameters = await parameter_repo.get_all(db, factory_id, device_id)
    
    return {
        "data": [ParameterResponse.model_validate(p).model_dump() for p in parameters]
    }


@router.patch("/devices/{device_id}/parameters/{param_id}", response_model=dict)
async def update_parameter(
    device_id: int,
    param_id: int,
    param_data: ParameterUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a parameter (display_name, unit, is_kpi_selected).
    
    Returns 404 if parameter not found or belongs to different factory/device.
    """
    factory_id = user._token_factory_id
    
    # Update parameter
    parameter = await parameter_repo.update(
        db, factory_id, device_id, param_id,
        param_data.model_dump(exclude_unset=True)
    )
    
    if not parameter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parameter not found"
        )
    
    logger.info(
        "parameter.updated",
        factory_id=factory_id,
        device_id=device_id,
        param_id=param_id,
        user_id=user.id
    )
    
    return {"data": ParameterResponse.model_validate(parameter).model_dump()}


@router.get("/devices/{device_id}/kpis/live", response_model=dict)
async def get_live_kpis(
    device_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get live KPI values for a device.
    
    Returns the most recent value for each selected parameter.
    Marks values as stale if they're older than 10 minutes.
    
    Returns 404 if device not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    # Verify device exists and belongs to factory
    device = await device_repo.get_by_id(db, factory_id, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get selected parameter keys
    selected_params = await parameter_repo.get_selected_keys(db, factory_id, device_id)
    
    # Get all parameters for metadata
    all_params = await parameter_repo.get_all(db, factory_id, device_id)
    param_metadata = {p.parameter_key: p for p in all_params}
    
    # Get live KPI values from InfluxDB
    kpis = await kpi_service.get_live_kpis(
        factory_id, device_id, selected_params, param_metadata
    )
    
    response = KPILiveResponse(
        device_id=device_id,
        timestamp=datetime.utcnow(),
        kpis=kpis
    )
    
    return {"data": response.model_dump()}


@router.get("/devices/{device_id}/kpis/history", response_model=dict)
async def get_kpi_history(
    device_id: int,
    parameter: str = Query(..., description="Parameter key"),
    start: datetime = Query(..., description="Start time (ISO format)"),
    end: datetime = Query(..., description="End time (ISO format)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (e.g., 1m, 5m, 1h, 1d)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical KPI data for a parameter.
    
    Auto-selects interval if not provided:
    - range < 2h → 1m
    - range < 24h → 5m
    - range < 7d → 1h
    - else → 1d
    
    Returns 404 if device not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    # Verify device exists and belongs to factory
    device = await device_repo.get_by_id(db, factory_id, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Verify parameter exists for this device
    parameters = await parameter_repo.get_all(db, factory_id, device_id)
    param_metadata = {p.parameter_key: p for p in parameters}
    
    if parameter not in param_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parameter not found"
        )
    
    # Get historical data from InfluxDB
    points, used_interval = await kpi_service.get_kpi_history(
        factory_id, device_id, parameter, start, end, interval
    )
    
    param = param_metadata[parameter]
    response = KPIHistoryResponse(
        parameter_key=parameter,
        display_name=param.display_name,
        unit=param.unit,
        interval=used_interval,
        points=points
    )
    
    return {"data": response.model_dump()}
