"""
WebSocket Manager for Real-time RFID Notifications
Handles WebSocket connections and broadcasts RFID events to connected clients
"""

from fastapi import WebSocket
from typing import List, Dict
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count = 0

    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        logger.info(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to RFID notification service",
            "timestamp": datetime.now().isoformat()
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return
            
        logger.info(f"📡 Broadcasting to {len(self.active_connections)} clients: {message.get('type', 'unknown')}")
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_rfid_scan(self, rfid_number: str, cassette_code: str = None, status: str = "success", message: str = None):
        """Broadcast RFID scan event"""
        await self.broadcast({
            "type": "rfid_scan",
            "rfid_number": rfid_number,
            "cassette_code": cassette_code,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast_rfid_assign(self, rfid_number: str, cassette_code: str, cassette_id: int, status: str = "success"):
        """Broadcast RFID assignment event"""
        await self.broadcast({
            "type": "rfid_assign",
            "rfid_number": rfid_number,
            "cassette_code": cassette_code,
            "cassette_id": cassette_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast_notification(self, title: str, message: str, notification_type: str = "info"):
        """Broadcast general notification"""
        await self.broadcast({
            "type": "notification",
            "notification_type": notification_type,  # info, success, warning, error
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def get_stats(self):
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.connection_count
        }


# Global WebSocket manager instance
ws_manager = ConnectionManager()
