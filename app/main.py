from fastapi import FastAPI, Depends, WebSocket, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.api import cassette
from app import crud, schemas
from app.rfid_service import rfid_service
import config
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Get the directory where main.py is located
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize FastAPI app
app = FastAPI(
    title="Cassette Tracking System API",
    description="RESTful API for managing Cassette Master with RFID tracking",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Middleware - Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"  # Allow all origins in development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(cassette.router)

# Mount static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve index.html at root
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend HTML application"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Cassette Tracking System API", "docs": "/api/docs"}


# Initialize database and start RFID service on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and start RFID background service"""
    init_db()
    print("✅ Application started successfully!")
    print(f"📚 API Documentation: http://{config.HOST}:{config.PORT}/api/docs")
    print(f"🔌 API Base URL: http://{config.HOST}:{config.PORT}/api")
    
    # Start RFID background service if enabled
    if config.RFID_SERVICE_ENABLED:
        print(f"🔄 Starting RFID Background Service (interval: {config.RFID_READ_INTERVAL}s)...")
        # Update service interval from config
        rfid_service.read_interval = config.RFID_READ_INTERVAL
        asyncio.create_task(rfid_service.start())
    else:
        print("⏸️  RFID Background Service is disabled (set RFID_SERVICE_ENABLED=true to enable)")

# Stop RFID service on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Stop RFID background service on shutdown"""
    print("🛑 Shutting down...")
    rfid_service.stop()
    print("✅ RFID service stopped")


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Cassette Tracking System API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "application": "Cassette Tracking System API",
        "version": "1.0.0"
    }

# Statistics endpoint for dashboard
@app.get("/api/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    try:
        cassette_count = crud.get_cassettes(db, skip=0, limit=1)["total"]
        
        return {
            "cassettes": cassette_count
        }
    except Exception as e:
        return {
            "cassettes": 0
        }

# RFID Service Status endpoint
@app.get("/api/rfid/status")
async def get_rfid_service_status():
    """Get RFID background service status including GPIO status"""
    return rfid_service.get_status()

# GPIO Control endpoints
@app.post("/api/gpio/mapping")
async def configure_gpio_mapping(rfid_number: str, output_name: str):
    """
    Configure RFID to GPIO output mapping
    
    Args:
        rfid_number: The RFID tag number
        output_name: Output name (DO0, DO1, DO2, DO3)
    """
    try:
        rfid_service.configure_rfid_gpio_mapping(rfid_number, output_name)
        return {
            "success": True,
            "message": f"Mapped RFID {rfid_number} to {output_name}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gpio/status")
async def get_gpio_status():
    """Get GPIO controller status and current output states"""
    from app.gpio_controller import gpio_controller
    return gpio_controller.get_status()

@app.post("/api/gpio/output/{output_name}")
async def set_gpio_output(output_name: str, value: int):
    """
    Manually set a GPIO output
    
    Args:
        output_name: Output name (DO0, DO1, DO2, DO3)
        value: 1 for HIGH, 0 for LOW
    """
    from app.gpio_controller import gpio_controller
    
    if value not in [0, 1]:
        raise HTTPException(status_code=400, detail="Value must be 0 or 1")
    
    success = gpio_controller.set_output(output_name, value)
    
    if success:
        return {
            "success": True,
            "message": f"{output_name} set to {'HIGH' if value else 'LOW'}"
        }
    else:
        raise HTTPException(status_code=400, detail=f"Failed to set {output_name}")

@app.post("/api/gpio/reset")
async def reset_all_gpio():
    """Reset all GPIO outputs to LOW"""
    from app.gpio_controller import gpio_controller
    gpio_controller.reset_all_outputs()
    return {"success": True, "message": "All outputs reset to LOW"}

# WebSocket endpoint for real-time RFID notifications
@app.websocket("/ws/rfid")
async def websocket_rfid_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time RFID event notifications"""
    from app.websocket_manager import ws_manager
    
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            await websocket.send_json({"type": "pong", "message": "Connection alive"})
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)

# RFID Transaction endpoints
@app.get("/api/transactions", response_model=schemas.RFIDTransactionListResponse)
async def get_all_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all RFID transactions with pagination"""
    return crud.get_rfid_transactions(db, skip=skip, limit=limit)

@app.get("/api/transactions/recent")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent RFID transactions"""
    transactions = crud.get_recent_rfid_transactions(db, limit=limit)
    return transactions

@app.get("/api/transactions/rfid/{rfid_number}")
async def get_transactions_by_rfid(
    rfid_number: str,
    db: Session = Depends(get_db)
):
    """Get all transactions for a specific RFID"""
    transactions = crud.get_rfid_transactions_by_rfid(db, rfid_number)
    return transactions


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG
    )
