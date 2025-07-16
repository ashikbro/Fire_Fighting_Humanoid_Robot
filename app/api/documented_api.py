"""
Enhanced API with comprehensive OpenAPI documentation
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from app.core.authentication import get_current_user, require_admin, require_operator
from app.core.validation import SensorDataInput, RobotMovementInput, NavigationGoalInput
from app.core.error_handling import logger
from app.core.config_manager import config

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Fire Fighting Humanoid Robot API",
        version="2.0.0",
        description="""
        ## 🔥 Fire Fighting Humanoid Robot Control API
        
        This API provides comprehensive control and monitoring capabilities for a fire-fighting humanoid robot.
        
        ### 🚀 Features
        - **Real-time fire detection** using computer vision
        - **Autonomous navigation** with SLAM and path planning
        - **Remote robot control** via REST API
        - **Sensor data monitoring** and analytics
        - **Incident management** and logging
        - **Security** with JWT authentication
        
        ### 🔐 Authentication
        Most endpoints require authentication using JWT tokens. Obtain a token by calling the `/auth/login` endpoint.
        
        ### 📱 Roles
        - **Admin**: Full access to all endpoints
        - **Operator**: Standard robot operation
        - **Viewer**: Read-only access
        
        ### 📊 Data Models
        The API uses standardized data models for sensor readings, robot commands, and system status.
        """,
        routes=app.routes,
        contact={
            "name": "Fire Fighting Robot Team",
            "email": "support@firebot.local",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        }
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/login endpoint"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service communication"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="Fire Fighting Robot API",
    description="Advanced API for Fire Fighting Humanoid Robot",
    version="2.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
    openapi_url="/api/v2/openapi.json"
)

app.openapi = custom_openapi

# Custom documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Interactive API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

# Response models
class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class HealthStatus(BaseModel):
    """System health status model"""
    overall_status: str = Field(..., description="Overall system status", example="ok")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    active_connections: int = Field(..., description="Number of active network connections")

class RobotStatus(BaseModel):
    """Robot status model"""
    battery_level: int = Field(..., ge=0, le=100, description="Battery level percentage")
    position: Dict[str, float] = Field(..., description="Robot position {x, y, z}")
    orientation: float = Field(..., description="Robot orientation in radians")
    system_status: str = Field(..., description="System status", example="online")
    active_mission: Optional[str] = Field(None, description="Current active mission")
    last_update: datetime = Field(default_factory=datetime.now, description="Last status update")

class FireDetection(BaseModel):
    """Fire detection result model"""
    detected: bool = Field(..., description="Whether fire was detected")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    location: Optional[Dict[str, float]] = Field(None, description="Fire location if detected")
    severity: Optional[str] = Field(None, description="Fire severity level")
    timestamp: datetime = Field(default_factory=datetime.now, description="Detection timestamp")

class IncidentReport(BaseModel):
    """Incident report model"""
    id: int = Field(..., description="Incident ID")
    event_type: str = Field(..., description="Type of incident")
    severity: str = Field(..., description="Incident severity")
    location: Optional[str] = Field(None, description="Incident location")
    timestamp: datetime = Field(..., description="Incident timestamp")
    status: str = Field(..., description="Incident status")
    response_time: Optional[float] = Field(None, description="Response time in seconds")

# API Endpoints

@app.get("/", 
         response_model=APIResponse,
         summary="API Root",
         description="Get basic API information and status")
async def root():
    """Root endpoint providing API information"""
    return APIResponse(
        success=True,
        message="Fire Fighting Humanoid Robot API v2.0",
        data={
            "version": "2.0.0",
            "status": "operational",
            "docs_url": "/docs",
            "health_url": "/health"
        }
    )

@app.get("/health",
         response_model=HealthStatus,
         summary="System Health Check",
         description="Get comprehensive system health status")
async def health_check():
    """Get system health status"""
    from app.core.health_monitoring import system_monitor
    health_summary = system_monitor.get_health_summary()
    
    return HealthStatus(
        overall_status=health_summary.get("overall_status", "unknown"),
        uptime_seconds=health_summary.get("uptime_seconds", 0),
        cpu_usage=health_summary.get("metrics", {}).get("cpu_usage", {}).get("value", 0),
        memory_usage=health_summary.get("metrics", {}).get("memory_usage", {}).get("value", 0),
        disk_usage=health_summary.get("metrics", {}).get("disk_usage", {}).get("value", 0),
        active_connections=health_summary.get("metrics", {}).get("network_connections", {}).get("value", 0)
    )

@app.post("/api/v2/sensors/reading",
          response_model=APIResponse,
          summary="Submit Sensor Reading",
          description="Submit sensor data for fire severity prediction",
          dependencies=[Depends(require_operator())],
          tags=["Sensors"])
async def submit_sensor_reading(
    sensor_data: SensorDataInput,
    current_user: dict = Depends(get_current_user)
):
    """Submit sensor reading and get fire severity prediction"""
    try:
        # Log sensor reading to database
        from app.db.database import log_sensor_reading
        reading_id = log_sensor_reading(
            temperature=sensor_data.temperature,
            smoke_density=sensor_data.smoke_density,
            gas_level=sensor_data.gas_level,
            humidity=sensor_data.humidity
        )
        
        # TODO: Implement fire severity prediction
        prediction = "low"  # Placeholder
        confidence = 0.85   # Placeholder
        
        return APIResponse(
            success=True,
            message="Sensor reading processed successfully",
            data={
                "reading_id": reading_id,
                "prediction": prediction,
                "confidence": confidence
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing sensor reading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process sensor reading"
        )

@app.post("/api/v2/robot/move",
          response_model=APIResponse,
          summary="Move Robot",
          description="Send movement command to the robot",
          dependencies=[Depends(require_operator())],
          tags=["Robot Control"])
async def move_robot(
    movement: RobotMovementInput,
    current_user: dict = Depends(get_current_user)
):
    """Send movement command to robot"""
    try:
        # TODO: Implement actual robot movement
        logger.info(f"Robot movement command: {movement.direction} at {movement.speed}% for {movement.duration}s")
        
        return APIResponse(
            success=True,
            message=f"Robot moving {movement.direction}",
            data={
                "direction": movement.direction,
                "speed": movement.speed,
                "duration": movement.duration,
                "operator": current_user.get("username")
            }
        )
        
    except Exception as e:
        logger.error(f"Error moving robot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move robot"
        )

@app.get("/api/v2/robot/status",
         response_model=RobotStatus,
         summary="Get Robot Status",
         description="Get current robot status and position",
         dependencies=[Depends(get_current_user)],
         tags=["Robot Status"])
async def get_robot_status():
    """Get current robot status"""
    # TODO: Get actual robot status
    return RobotStatus(
        battery_level=85,
        position={"x": 10.5, "y": 20.3, "z": 0.0},
        orientation=1.57,
        system_status="online",
        active_mission="patrol"
    )

@app.get("/api/v2/incidents",
         response_model=List[IncidentReport],
         summary="Get Incident History",
         description="Get list of recorded incidents",
         dependencies=[Depends(require_admin)],
         tags=["Incident Management"])
async def get_incidents(
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of incidents to return")
):
    """Get incident history"""
    try:
        from app.db.database import get_incident_history
        incidents = get_incident_history(limit)
        
        return [
            IncidentReport(
                id=incident['id'],
                event_type=incident['event_type'],
                severity=incident['severity'] or 'unknown',
                location=incident['location'],
                timestamp=datetime.fromisoformat(incident['timestamp']),
                status=incident['status'],
                response_time=incident['response_time']
            )
            for incident in incidents
        ]
        
    except Exception as e:
        logger.error(f"Error getting incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve incidents"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return APIResponse(
        success=False,
        message=exc.detail,
        data={"status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return APIResponse(
        success=False,
        message="Internal server error",
        data={"error_type": type(exc).__name__}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
