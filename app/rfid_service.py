"""
RFID Background Service
Continuously monitors RFID reader for new tags
Integrates with GPIO controller for hardware output control
"""

import asyncio
import logging
from datetime import datetime
from app.rfid_reader import read_rfid_tag
from app.gpio_controller import gpio_controller

logger = logging.getLogger(__name__)

class RFIDBackgroundService:
    def __init__(self, read_interval=5):
        """
        Initialize RFID background service
        
        Args:
            read_interval (int): Interval in seconds between RFID reads
        """
        self.read_interval = read_interval
        self.is_running = False
        self.last_rfid = None
        self.last_read_time = None
        self.read_count = 0
        self.error_count = 0
        
        # Initialize GPIO controller
        gpio_controller.initialize()
        
    async def start(self):
        """Start the background RFID reading service"""
        if self.is_running:
            logger.warning("RFID service is already running")
            return
            
        self.is_running = True
        logger.info(f"🚀 RFID Background Service started (interval: {self.read_interval}s)")
        
        while self.is_running:
            try:
                await self._read_and_process()
                await asyncio.sleep(self.read_interval)
            except asyncio.CancelledError:
                logger.info("RFID service cancelled")
                break
            except Exception as e:
                logger.error(f"Error in RFID service: {e}")
                self.error_count += 1
                await asyncio.sleep(self.read_interval)
    
    async def _read_and_process(self):
        """Read RFID tag and process it"""
        try:
            # Run blocking RFID read in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, read_rfid_tag)
            
            self.read_count += 1
            current_time = datetime.now()
            
            if result['success']:
                rfid_number = result['rfid_number']
                
                # Only log if it's a new/different RFID
                if rfid_number != self.last_rfid:
                    logger.info(f"📡 New RFID detected: {rfid_number}")
                    self.last_rfid = rfid_number
                    self.last_read_time = current_time
                    
                    # Trigger GPIO output based on RFID
                    triggered_output = await self._trigger_gpio(rfid_number)
                    
                    # Process RFID (log transaction, send notifications)
                    await self._on_rfid_detected(rfid_number, triggered_output)
                    
            else:
                # No tag or error - only log occasionally to avoid spam
                if self.read_count % 12 == 0:  # Log every minute (12 * 5 seconds)
                    logger.debug(f"RFID reader status: {result['message']}")
                    
        except Exception as e:
            logger.error(f"Error reading RFID: {e}")
            self.error_count += 1
    
    async def _trigger_gpio(self, rfid_number: str) -> str:
        """
        Trigger GPIO output based on RFID number
        Uses mapping from database (gpio_output field in CassetteMaster)
        
        Args:
            rfid_number: The detected RFID number
            
        Returns:
            The output name that was triggered, or None
        """
        try:
            loop = asyncio.get_event_loop()
            
            # First get the output mapping from database
            output_name = await loop.run_in_executor(
                None, 
                gpio_controller.get_output_for_rfid, 
                rfid_number
            )
            
            if output_name:
                # Trigger the output
                success = await loop.run_in_executor(
                    None,
                    gpio_controller.set_output,
                    output_name,
                    1  # HIGH
                )
                
                if success:
                    logger.info(f"⚡ GPIO {output_name} triggered HIGH for RFID {rfid_number}")
                    return output_name
                    
            return None
        except Exception as e:
            logger.error(f"Error triggering GPIO: {e}")
            return None
    
    async def _on_rfid_detected(self, rfid_number: str, triggered_output: str = None):
        """
        Called when a new RFID tag is detected
        Logs transaction, sends notifications, and triggers webhooks
        
        Args:
            rfid_number (str): The detected RFID number
            triggered_output (str): The GPIO output that was triggered (if any)
        """
        from app.database import SessionLocal
        from app import crud, schemas
        from app.websocket_manager import ws_manager
        import json
        
        db = SessionLocal()
        
        try:
            # Check if RFID is already assigned to a cassette
            cassette = crud.get_cassette_by_rfid(db, rfid_number)
            
            if cassette:
                # Build extra data with GPIO info
                extra_info = {"desc": cassette.desc}
                if triggered_output:
                    extra_info["gpio_output"] = triggered_output
                
                # RFID is assigned - log scan event
                transaction_data = schemas.RFIDTransactionCreate(
                    rfid_number=rfid_number,
                    cassette_id=cassette.id,
                    cassette_code=cassette.cassette_code,
                    event_type="scan",
                    status="success",
                    message=f"RFID scanned for cassette {cassette.cassette_code}" + 
                            (f" → {triggered_output} HIGH" if triggered_output else ""),
                    extra_data=json.dumps(extra_info)
                )
                
                # Save to database
                crud.create_rfid_transaction(db, transaction_data)
                
                # Broadcast WebSocket notification
                await ws_manager.broadcast_rfid_scan(
                    rfid_number=rfid_number,
                    cassette_code=cassette.cassette_code,
                    status="success",
                    message=f"Cassette {cassette.cassette_code} scanned" + 
                            (f" → {triggered_output}" if triggered_output else "")
                )
                
                # Send notification
                await ws_manager.broadcast_notification(
                    title="RFID Scanned",
                    message=f"Cassette '{cassette.cassette_code}' detected" + 
                            (f" → {triggered_output} HIGH" if triggered_output else ""),
                    notification_type="success"
                )
                
                logger.info(f"✅ RFID {rfid_number} scanned for cassette {cassette.cassette_code}" + 
                           (f" → {triggered_output} HIGH" if triggered_output else ""))
                
            else:
                # RFID not assigned - log as unassigned scan
                extra_info = {}
                if triggered_output:
                    extra_info["gpio_output"] = triggered_output
                
                transaction_data = schemas.RFIDTransactionCreate(
                    rfid_number=rfid_number,
                    cassette_id=None,
                    cassette_code=None,
                    event_type="scan",
                    status="pending",
                    message="RFID detected but not assigned to any cassette" + 
                            (f" → {triggered_output} HIGH" if triggered_output else ""),
                    extra_data=json.dumps(extra_info) if extra_info else None
                )
                
                # Save to database
                crud.create_rfid_transaction(db, transaction_data)
                
                # Broadcast WebSocket notification
                await ws_manager.broadcast_rfid_scan(
                    rfid_number=rfid_number,
                    cassette_code=None,
                    status="pending",
                    message="Unassigned RFID detected" + 
                            (f" → {triggered_output}" if triggered_output else "")
                )
                
                # Send warning notification
                await ws_manager.broadcast_notification(
                    title="Unassigned RFID Detected",
                    message=f"RFID {rfid_number} is not assigned to any cassette" + 
                            (f" → {triggered_output} HIGH" if triggered_output else ""),
                    notification_type="warning"
                )
                
                logger.warning(f"⚠️ Unassigned RFID detected: {rfid_number}" + 
                              (f" → {triggered_output} HIGH" if triggered_output else ""))
                
        except Exception as e:
            logger.error(f"Error processing RFID detection: {e}")
            
            # Log error transaction
            try:
                transaction_data = schemas.RFIDTransactionCreate(
                    rfid_number=rfid_number,
                    cassette_id=None,
                    cassette_code=None,
                    event_type="scan",
                    status="error",
                    message=f"Error processing RFID: {str(e)}",
                    extra_data=None
                )
                crud.create_rfid_transaction(db, transaction_data)
            except:
                pass
                
        finally:
            db.close()
    
    def configure_rfid_gpio_mapping(self, rfid_number: str, output_name: str):
        """
        Configure RFID to GPIO output mapping
        
        Args:
            rfid_number: The RFID tag number
            output_name: Output name (DO0, DO1, DO2, DO3)
        """
        gpio_controller.configure_rfid_mapping(rfid_number, output_name)
    
    def stop(self):
        """Stop the background service"""
        logger.info("🛑 Stopping RFID Background Service...")
        self.is_running = False
        gpio_controller.cleanup()
    
    def get_status(self):
        """Get service status"""
        gpio_status = gpio_controller.get_status()
        
        return {
            "is_running": self.is_running,
            "read_interval": self.read_interval,
            "total_reads": self.read_count,
            "error_count": self.error_count,
            "last_rfid": self.last_rfid,
            "last_read_time": self.last_read_time.isoformat() if self.last_read_time else None,
            "gpio": gpio_status
        }


# Global service instance
rfid_service = RFIDBackgroundService(read_interval=5)
