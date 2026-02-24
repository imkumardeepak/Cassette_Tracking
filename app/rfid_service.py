"""
RFID Background Service
Continuously monitors RFID reader for new tags
Integrates with Modbus RTU relay controller for hardware output control

Working Flow:
1. Background loop runs every `read_interval` seconds (default 5s)
2. Sends READ command to RFID reader via TCP
3. If a tag is detected:
   a. Check if it's a NEW tag (not seen within cooldown period)
   b. If NEW → look up cassette in DB → trigger mapped relay ON → insert transaction → send WebSocket notification
   c. If SAME tag still present → keep relay ON (reset auto-off timer), do NOT insert duplicate transaction
4. If NO tag detected:
   a. Turn OFF any active relay
   b. Clear current RFID (but keep it in recent_rfids for cooldown)
5. Auto-off: If relay has been ON for `output_duration` seconds without RFID refresh, turn it OFF
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
        
        # Relay auto-off tracking
        self.active_output = None  # Currently active relay output
        self.output_trigger_time = None  # When the output was triggered
        self.output_duration = 5  # Seconds to keep relay ON
        
        # Duplicate prevention: track recently scanned RFIDs with timestamps
        # Only insert a transaction if the RFID hasn't been seen within cooldown_seconds
        self.recent_rfids = {}  # {rfid_number: last_seen_datetime}
        self.cooldown_seconds = 30  # Don't re-log same RFID within 30 seconds
        
        # Initialize relay controller
        gpio_controller.initialize()
        
    async def start(self):
        """Start the background RFID reading service"""
        if self.is_running:
            logger.warning("RFID service is already running")
            return
            
        self.is_running = True
        logger.info(f"🚀 RFID Background Service started (interval: {self.read_interval}s, cooldown: {self.cooldown_seconds}s)")
        
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
    
    def _is_new_rfid(self, rfid_number: str) -> bool:
        """
        Check if an RFID tag should be treated as a NEW scan.
        Returns True only if the RFID hasn't been seen within the cooldown period.
        This prevents duplicate transactions when a tag is removed and re-placed.
        """
        now = datetime.now()
        
        # Clean up old entries (older than cooldown)
        expired = [k for k, v in self.recent_rfids.items() 
                   if (now - v).total_seconds() > self.cooldown_seconds]
        for k in expired:
            del self.recent_rfids[k]
        
        # Check if this RFID was recently seen
        if rfid_number in self.recent_rfids:
            elapsed = (now - self.recent_rfids[rfid_number]).total_seconds()
            logger.debug(f"RFID {rfid_number} was seen {elapsed:.1f}s ago (cooldown: {self.cooldown_seconds}s)")
            return False  # Not new — within cooldown
        
        return True  # Genuinely new RFID
    
    def _mark_rfid_seen(self, rfid_number: str):
        """Mark an RFID as recently seen (resets cooldown timer)"""
        self.recent_rfids[rfid_number] = datetime.now()

    async def _check_and_auto_off_output(self):
        """Check if active output should be turned off (after output_duration seconds)"""
        if self.active_output and self.output_trigger_time:
            elapsed = (datetime.now() - self.output_trigger_time).total_seconds()
            if elapsed >= self.output_duration:
                # Turn off the output
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    gpio_controller.set_output,
                    self.active_output,
                    0  # OFF
                )
                logger.info(f"⏱️ Relay {self.active_output} auto-OFF after {self.output_duration}s")
                self.active_output = None
                self.output_trigger_time = None
    
    async def _read_and_process(self):
        """Read RFID tag and process it"""
        try:
            # Check if we need to auto-turn-off the output
            await self._check_and_auto_off_output()
            
            # Run blocking RFID read in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, read_rfid_tag)
            
            self.read_count += 1
            current_time = datetime.now()
            
            if result['success']:
                rfid_number = result['rfid_number']
                
                # Check if this is a genuinely NEW RFID (not seen within cooldown)
                is_new = self._is_new_rfid(rfid_number)
                is_different = rfid_number != self.last_rfid
                
                if is_new and is_different:
                    # ── GENUINELY NEW RFID ──
                    logger.info(f"📡 New RFID detected: {rfid_number}")
                    self.last_rfid = rfid_number
                    self.last_read_time = current_time
                    self._mark_rfid_seen(rfid_number)
                    
                    # Turn off previous output before triggering new one
                    if self.active_output:
                        await loop.run_in_executor(
                            None,
                            gpio_controller.set_output,
                            self.active_output,
                            0  # OFF
                        )
                        logger.info(f"🔄 Relay {self.active_output} OFF (new RFID detected)")
                    
                    # Trigger relay output based on RFID
                    triggered_output = await self._trigger_gpio(rfid_number)
                    
                    # Track the active output for auto-off
                    if triggered_output:
                        self.active_output = triggered_output
                        self.output_trigger_time = current_time
                    
                    # Process RFID — INSERT transaction record + send notifications
                    await self._on_rfid_detected(rfid_number, triggered_output)
                    
                elif is_different and not is_new:
                    # ── SAME RFID RE-PLACED WITHIN COOLDOWN ──
                    # Trigger relay again but do NOT insert duplicate transaction
                    logger.info(f"🔄 RFID {rfid_number} re-detected within cooldown — relay only, no transaction")
                    self.last_rfid = rfid_number
                    self.last_read_time = current_time
                    self._mark_rfid_seen(rfid_number)
                    
                    # Turn off previous output
                    if self.active_output:
                        await loop.run_in_executor(
                            None,
                            gpio_controller.set_output,
                            self.active_output,
                            0
                        )
                    
                    # Trigger relay
                    triggered_output = await self._trigger_gpio(rfid_number)
                    if triggered_output:
                        self.active_output = triggered_output
                        self.output_trigger_time = current_time
                else:
                    # ── SAME RFID STILL PRESENT (continuous read) ──
                    # Just keep the relay ON, refresh the auto-off timer
                    if self.active_output:
                        self.output_trigger_time = current_time
                    self._mark_rfid_seen(rfid_number)
                    
            else:
                # No tag detected - turn off active relay
                if self.active_output:
                    await loop.run_in_executor(
                        None,
                        gpio_controller.set_output,
                        self.active_output,
                        0  # OFF
                    )
                    logger.info(f"📴 Relay {self.active_output} OFF (no RFID tag)")
                    self.active_output = None
                    self.output_trigger_time = None
                
                # Clear current RFID (but recent_rfids keeps the cooldown active)
                self.last_rfid = None
                
                # Only log occasionally to avoid spam
                if self.read_count % 12 == 0:  # Log every minute (12 * 5 seconds)
                    logger.debug(f"RFID reader status: {result['message']}")
                    
        except Exception as e:
            logger.error(f"Error reading RFID: {e}")
            self.error_count += 1
    
    async def _trigger_gpio(self, rfid_number: str) -> str:
        """
        Trigger relay output based on RFID number
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
                    logger.info(f"⚡ Relay {output_name} triggered ON for RFID {rfid_number}")
                    return output_name
                    
            return None
        except Exception as e:
            logger.error(f"Error triggering relay: {e}")
            return None
    
    async def _on_rfid_detected(self, rfid_number: str, triggered_output: str = None):
        """
        Called when a new RFID tag is detected.
        
        ONLY processes RFIDs that are assigned in Cassette Master.
        Unassigned/unknown RFIDs are ignored (no transaction, no production log).
        
        For assigned RFIDs:
        1. Close any open production log (sets to_date = now)
        2. Create a new production log (from_date = now, status = open)
        3. Insert RFID transaction record
        4. Send WebSocket notifications
        """
        from app.database import SessionLocal
        from app import crud, schemas
        from app.websocket_manager import ws_manager
        import json
        
        db = SessionLocal()
        
        try:
            # Check if RFID is assigned to a cassette in master table
            cassette = crud.get_cassette_by_rfid(db, rfid_number)
            
            if not cassette:
                # ── UNASSIGNED RFID — SKIP completely ──
                # No transaction record, no production log
                logger.warning(f"⚠️ RFID {rfid_number} not found in Cassette Master — skipping (no records saved)")
                
                # Only send WebSocket notification so UI shows warning
                await ws_manager.broadcast_rfid_scan(
                    rfid_number=rfid_number,
                    cassette_code=None,
                    status="pending",
                    message="Unassigned RFID — not in Cassette Master"
                )
                await ws_manager.broadcast_notification(
                    title="Unknown RFID",
                    message=f"RFID {rfid_number[:16]}... not assigned to any cassette",
                    notification_type="warning"
                )
                return  # ← EXIT: no DB records for unassigned RFIDs
            
            # ── ASSIGNED RFID — FULL PROCESSING ──
            
            # 1. Check currently open production log
            open_log = crud.get_open_production_log(db)
            log_id = None
            
            if open_log and open_log.rfid_number != rfid_number:
                # Close it because it's a different RFID
                closed_count = crud.close_open_production_logs(db)
                if closed_count > 0:
                    logger.info(f"📋 Closed {closed_count} open production log(s)")
                open_log = None
            
            if not open_log:
                # 2. Create a new production log for this cassette session
                log_data = schemas.ProductionLogCreate(
                    cassette_id=cassette.id,
                    cassette_code=cassette.cassette_code,
                    rfid_number=rfid_number,
                    relay_output=triggered_output,
                    from_date=datetime.now()
                )
                new_log = crud.create_production_log(db, log_data)
                log_id = new_log.id
                logger.info(f"📋 Production log #{new_log.id} opened for cassette {cassette.cassette_code}")
                
                # 3. Create RFID transaction record ONLY ONCE per session switch
                extra_info = {"desc": cassette.desc, "production_log_id": log_id}
                if triggered_output:
                    extra_info["relay_output"] = triggered_output
                
                transaction_data = schemas.RFIDTransactionCreate(
                    rfid_number=rfid_number,
                    cassette_id=cassette.id,
                    cassette_code=cassette.cassette_code,
                    event_type="scan",
                    status="success",
                    message=f"Cassette {cassette.cassette_code} scanned" + 
                            (f" → {triggered_output} ON" if triggered_output else ""),
                    extra_data=json.dumps(extra_info)
                )
                crud.create_rfid_transaction(db, transaction_data)
            else:
                log_id = open_log.id
                logger.info(f"📋 Keeping open production log #{log_id} active for cassette {cassette.cassette_code}")
            
            # 4. Send WebSocket notifications
            await ws_manager.broadcast_rfid_scan(
                rfid_number=rfid_number,
                cassette_code=cassette.cassette_code,
                status="success",
                message=f"Cassette {cassette.cassette_code} scanned" + 
                        (f" → {triggered_output}" if triggered_output else "")
            )
            await ws_manager.broadcast_notification(
                title="RFID Scanned",
                message=f"Cassette '{cassette.cassette_code}' detected" + 
                        (f" → {triggered_output} ON" if triggered_output else ""),
                notification_type="success"
            )
            
            logger.info(f"✅ RFID {rfid_number} → cassette {cassette.cassette_code}" + 
                       (f" → {triggered_output} ON" if triggered_output else ""))
                
        except Exception as e:
            logger.error(f"Error processing RFID detection: {e}")
                
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
        
        # Calculate remaining time if output is active
        remaining_seconds = None
        if self.active_output and self.output_trigger_time:
            elapsed = (datetime.now() - self.output_trigger_time).total_seconds()
            remaining_seconds = max(0, self.output_duration - elapsed)
        
        return {
            "is_running": self.is_running,
            "read_interval": self.read_interval,
            "cooldown_seconds": self.cooldown_seconds,
            "total_reads": self.read_count,
            "error_count": self.error_count,
            "last_rfid": self.last_rfid,
            "last_read_time": self.last_read_time.isoformat() if self.last_read_time else None,
            "active_output": self.active_output,
            "output_duration": self.output_duration,
            "output_remaining_seconds": remaining_seconds,
            "recent_rfids_count": len(self.recent_rfids),
            "gpio": gpio_status
        }


# Global service instance
rfid_service = RFIDBackgroundService(read_interval=5)
