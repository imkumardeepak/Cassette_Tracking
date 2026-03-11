"""
RFID Background Service
Continuously monitors RFID reader for new tags.
Supports PAIR detection — processes multiple RFID tags simultaneously.
Integrates with Modbus RTU relay controller for hardware output control.

Working Flow:
1. Background loop runs every `read_interval` seconds (default 5s)
2. Sends READ command to RFID reader via TCP
3. If tag(s) detected:
   a. Check each tag — is it NEW (not seen within cooldown)?
   b. For NEW tags → look up cassette → trigger relay → create production log + transaction → WS notification
   c. For SAME tags still present → keep relays ON (refresh timers)
   d. For tags REMOVED since last read → turn OFF their relays → close production log
4. If NO tags detected:
   a. Turn OFF all active relays
   b. Close all open production logs for those RFIDs
5. Auto-off: If a relay has been ON for `output_duration` seconds without refresh, turn it OFF
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
        Initialize RFID background service with pair support.
        
        Args:
            read_interval (int): Interval in seconds between RFID reads
        """
        self.read_interval = read_interval
        self.is_running = False
        self.last_rfids = set()        # Set of currently detected RFID tags (supports pairs)
        self.last_read_time = None
        self.read_count = 0
        self.error_count = 0
        
        # Relay auto-off tracking (supports multiple simultaneous outputs)
        # Format: {rfid_number: {'output': str, 'time': datetime}}
        self.active_outputs = {}
        self.output_duration = 5       # Seconds to keep relay ON
        
        # Duplicate prevention: track recently scanned RFIDs with timestamps
        self.recent_rfids = {}         # {rfid_number: last_seen_datetime}
        self.cooldown_seconds = 30     # Don't re-log same RFID within 30 seconds
        
        # Initialize relay controller
        gpio_controller.initialize()

    async def start(self):
        """Start the background RFID reading service"""
        self.is_running = True
        logger.info(f"🔄 Starting RFID Background Service (interval: {self.read_interval}s)...")
        
        while self.is_running:
            try:
                await self._read_and_process()
            except Exception as e:
                logger.error(f"Error in RFID service loop: {e}")
                self.error_count += 1
            
            await asyncio.sleep(self.read_interval)

    def _is_new_rfid(self, rfid_number: str) -> bool:
        """Check if this RFID has been seen recently (within cooldown period)"""
        if rfid_number not in self.recent_rfids:
            return True
        
        last_seen = self.recent_rfids[rfid_number]
        elapsed = (datetime.now() - last_seen).total_seconds()
        return elapsed > self.cooldown_seconds

    def _mark_rfid_seen(self, rfid_number: str):
        """Mark an RFID as recently seen (for cooldown tracking)"""
        self.recent_rfids[rfid_number] = datetime.now()
        
        # Cleanup old entries (older than 5 minutes)
        cutoff = datetime.now()
        expired = [
            rfid for rfid, ts in self.recent_rfids.items()
            if (cutoff - ts).total_seconds() > 300
        ]
        for rfid in expired:
            del self.recent_rfids[rfid]

    async def _check_and_auto_off_outputs(self):
        """Check if any active outputs should be turned off (after output_duration seconds)"""
        expired = []
        for rfid, output_info in self.active_outputs.items():
            elapsed = (datetime.now() - output_info['time']).total_seconds()
            if elapsed >= self.output_duration:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    gpio_controller.set_output,
                    output_info['output'],
                    0  # OFF
                )
                logger.info(f"⏱️ Relay {output_info['output']} auto-OFF after {self.output_duration}s")
                expired.append(rfid)
        
        for rfid in expired:
            del self.active_outputs[rfid]

    async def _read_and_process(self):
        """Read RFID tags and process all detected tags (supports pairs)"""
        try:
            # Check auto-off for all active outputs
            await self._check_and_auto_off_outputs()
            
            # Read RFID tags from hardware
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, read_rfid_tag)
            
            self.read_count += 1
            current_time = datetime.now()
            
            if result['success']:
                # Get ALL detected tags (pair support)
                detected_rfids = set(result.get('rfid_numbers', [result['rfid_number']]))
                previous_rfids = self.last_rfids.copy()
                
                # ── Tags REMOVED (were present before, now gone) ──
                gone_rfids = previous_rfids - detected_rfids
                for rfid in gone_rfids:
                    # Turn off relay for removed tag
                    if rfid in self.active_outputs:
                        output_info = self.active_outputs[rfid]
                        await loop.run_in_executor(
                            None, gpio_controller.set_output, output_info['output'], 0
                        )
                        logger.info(f"📴 Relay {output_info['output']} OFF (RFID {rfid[:16]}... removed)")
                        del self.active_outputs[rfid]
                    # Close production log for removed RFID
                    await self._on_rfid_removed(rfid)
                
                # ── Process each detected tag ──
                for rfid_number in detected_rfids:
                    is_new = self._is_new_rfid(rfid_number)
                    is_different = rfid_number not in previous_rfids
                    
                    if is_new and is_different:
                        # ── GENUINELY NEW RFID ──
                        logger.info(f"📡 New RFID detected: {rfid_number}")
                        self._mark_rfid_seen(rfid_number)
                        
                        # Trigger relay output
                        triggered_output = await self._trigger_gpio(rfid_number)
                        if triggered_output:
                            self.active_outputs[rfid_number] = {
                                'output': triggered_output,
                                'time': current_time
                            }
                        
                        # Process — create production log + transaction + WS notification
                        await self._on_rfid_detected(rfid_number, triggered_output)
                        
                    elif is_different and not is_new:
                        # ── RE-PLACED WITHIN COOLDOWN — relay only, no new transaction ──
                        logger.info(f"🔄 RFID {rfid_number[:16]}... re-detected within cooldown — relay only")
                        self._mark_rfid_seen(rfid_number)
                        
                        triggered_output = await self._trigger_gpio(rfid_number)
                        if triggered_output:
                            self.active_outputs[rfid_number] = {
                                'output': triggered_output,
                                'time': current_time
                            }
                    else:
                        # ── SAME RFID STILL PRESENT — refresh timer ──
                        if rfid_number in self.active_outputs:
                            self.active_outputs[rfid_number]['time'] = current_time
                        self._mark_rfid_seen(rfid_number)
                
                # Update state
                self.last_rfids = detected_rfids
                self.last_read_time = current_time
                
                if len(detected_rfids) > 1:
                    logger.info(f"📡 Pair detected: {len(detected_rfids)} tags — {', '.join(list(detected_rfids)[:3])}")
                
            else:
                # No tags detected — turn off all active relays and close logs
                if self.active_outputs:
                    for rfid, output_info in list(self.active_outputs.items()):
                        await loop.run_in_executor(
                            None, gpio_controller.set_output, output_info['output'], 0
                        )
                        logger.info(f"📴 Relay {output_info['output']} OFF (no RFID tags)")
                        # Close production log for this RFID
                        await self._on_rfid_removed(rfid)
                    self.active_outputs.clear()
                
                self.last_rfids.clear()
                
                if self.read_count % 12 == 0:
                    logger.debug(f"RFID reader status: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error reading RFID: {e}")
            self.error_count += 1

    async def _trigger_gpio(self, rfid_number: str) -> str:
        """
        Trigger GPIO output for a detected RFID tag.
        Returns the output name that was triggered, or None.
        """
        try:
            # Check if this RFID has a relay mapping
            output_name = gpio_controller.get_mapped_output(rfid_number)
            
            if output_name:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    gpio_controller.set_output,
                    output_name,
                    1  # ON
                )
                logger.info(f"⚡ Relay {output_name} ON for RFID {rfid_number[:16]}...")
                return output_name
            else:
                logger.debug(f"No relay mapping found for RFID {rfid_number[:16]}...")
                return None
        except Exception as e:
            logger.error(f"Error triggering GPIO for RFID {rfid_number}: {e}")
            return None

    async def _on_rfid_detected(self, rfid_number: str, triggered_output: str = None):
        """
        Called when a genuinely new RFID tag is detected.
        
        For assigned RFIDs (in Cassette Master):
        1. Check if there's already an open production log for THIS specific RFID
        2. If not, create a new production log + RFID transaction  
        3. Send WebSocket notifications
        
        For unassigned RFIDs: send warning via WebSocket only.
        """
        from app.database import SessionLocal
        from app import crud, schemas
        from app.websocket_manager import ws_manager
        import json
        
        db = SessionLocal()
        
        try:
            # Look up cassette by RFID
            cassette = crud.get_cassette_by_rfid(db, rfid_number)
            
            if not cassette:
                # Unassigned RFID — warn only, no DB records
                logger.warning(f"⚠️ RFID {rfid_number} not found in Cassette Master — skipping")
                
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
                return
            
            # Check if there's already an open production log for THIS specific RFID
            open_log = crud.get_open_production_log_by_rfid(db, rfid_number)
            
            if not open_log:
                # Create new production log for this cassette session
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
                
                # Create RFID transaction record
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
                logger.debug(f"📋 Keeping open production log #{log_id} for cassette {cassette.cassette_code}")
            
            # Send WebSocket notifications
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
            
        except Exception as e:
            logger.error(f"Error processing RFID detection: {e}")
        finally:
            db.close()

    async def _on_rfid_removed(self, rfid_number: str):
        """Called when an RFID tag is no longer detected. Closes its production log."""
        from app.database import SessionLocal
        from app import crud
        
        db = SessionLocal()
        try:
            closed = crud.close_production_logs_by_rfid(db, rfid_number)
            if closed:
                logger.info(f"📋 Production log closed for RFID {rfid_number[:16]}... (tag removed)")
        except Exception as e:
            logger.error(f"Error closing production log for removed RFID: {e}")
        finally:
            db.close()

    def configure_rfid_gpio_mapping(self, rfid_number: str, output_name: str):
        """
        Configure a mapping between an RFID tag and a relay output.
        When this RFID is detected, the specified relay will be activated.
        """
        gpio_controller.configure_rfid_mapping(rfid_number, output_name)

    def stop(self):
        """Stop the background RFID reading service"""
        self.is_running = False
        logger.info("🛑 Stopping RFID Background Service...")
        gpio_controller.cleanup()

    def get_status(self):
        """Get the current status of the RFID service"""
        gpio_status = gpio_controller.get_status()
        
        # Build active output details
        active_output_details = {}
        for rfid, info in self.active_outputs.items():
            elapsed = (datetime.now() - info['time']).total_seconds()
            active_output_details[info['output']] = {
                'rfid': rfid,
                'remaining_seconds': max(0, self.output_duration - elapsed)
            }
        
        last_rfids_list = list(self.last_rfids)
        
        return {
            "is_running": self.is_running,
            "read_interval": self.read_interval,
            "cooldown_seconds": self.cooldown_seconds,
            "total_reads": self.read_count,
            "error_count": self.error_count,
            "last_rfid": last_rfids_list[0] if last_rfids_list else None,   # backward compat
            "last_rfids": last_rfids_list,                                   # all detected tags
            "last_read_time": self.last_read_time.isoformat() if self.last_read_time else None,
            "active_output": list(active_output_details.keys())[0] if active_output_details else None,
            "active_outputs": active_output_details,
            "output_duration": self.output_duration,
            "output_remaining_seconds": None,
            "recent_rfids_count": len(self.recent_rfids),
            "gpio": gpio_status
        }


# Global service instance
rfid_service = RFIDBackgroundService(read_interval=5)
