"""
RFID Background Service — Paired Cassette Detection

Monitors RFID reader for EXACTLY TWO tags simultaneously.
Cassettes always come in pairs — only processes when both tags are detected.

Working Flow:
1. Background loop runs every `read_interval` seconds (default 5s)
2. Sends READ command to RFID reader via TCP
3. If EXACTLY 2 tags detected (pair):
   a. Look up both cassettes in Cassette Master
   b. Trigger both corresponding relays
   c. Create ONE production log for the pair (rfid1 + rfid2)
   d. Create ONE RFID transaction for the pair
   e. Send WebSocket notification
4. If 1 tag detected:
   a. Log warning — waiting for pair
5. If 0 tags detected:
   a. Turn OFF all active relays
   b. Close open production log for previous pair
6. If pair CHANGES:
   a. Close old production log
   b. Open new production log for new pair
"""

import asyncio
import logging
from datetime import datetime
from app.rfid_reader import read_rfid_tag
from app.gpio_controller import gpio_controller

logger = logging.getLogger(__name__)


class RFIDBackgroundService:
    def __init__(self, read_interval=5):
        self.read_interval = read_interval
        self.is_running = False
        self.last_pair = None          # frozenset of 2 RFIDs (or None)
        self.last_read_time = None
        self.read_count = 0
        self.error_count = 0
        
        # Relay auto-off tracking: {rfid: {'output': str, 'time': datetime}}
        self.active_outputs = {}
        self.output_duration = 5       # Seconds to keep relay ON
        
        # Duplicate prevention
        self.recent_pairs = {}         # {frozenset: last_seen_datetime}
        self.cooldown_seconds = 30
        
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

    def _is_new_pair(self, pair_key: frozenset) -> bool:
        """Check if this pair has been seen recently (within cooldown period)"""
        if pair_key not in self.recent_pairs:
            return True
        last_seen = self.recent_pairs[pair_key]
        elapsed = (datetime.now() - last_seen).total_seconds()
        return elapsed > self.cooldown_seconds

    def _mark_pair_seen(self, pair_key: frozenset):
        """Mark a pair as recently seen"""
        self.recent_pairs[pair_key] = datetime.now()
        
        # Cleanup old entries (older than 5 minutes)
        cutoff = datetime.now()
        expired = [
            k for k, ts in self.recent_pairs.items()
            if (cutoff - ts).total_seconds() > 300
        ]
        for k in expired:
            del self.recent_pairs[k]

    async def _check_and_auto_off_outputs(self):
        """Check if any active outputs should be turned off"""
        expired = []
        for rfid, output_info in self.active_outputs.items():
            elapsed = (datetime.now() - output_info['time']).total_seconds()
            if elapsed >= self.output_duration:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, gpio_controller.set_output, output_info['output'], 0
                )
                logger.info(f"⏱️ Relay {output_info['output']} auto-OFF after {self.output_duration}s")
                expired.append(rfid)
        
        for rfid in expired:
            del self.active_outputs[rfid]

    async def _read_and_process(self):
        """Read RFID tags and process ONLY when exactly 2 tags detected (pair)"""
        try:
            await self._check_and_auto_off_outputs()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, read_rfid_tag)
            
            self.read_count += 1
            current_time = datetime.now()
            
            if result['success']:
                detected_rfids = result.get('rfid_numbers', [result['rfid_number']])
                
                if len(detected_rfids) == 2:
                    # ═══ PAIR DETECTED ═══
                    rfid1, rfid2 = sorted(detected_rfids)  # Sort for consistency
                    pair_key = frozenset([rfid1, rfid2])
                    
                    if pair_key != self.last_pair:
                        # ── NEW PAIR (different from previous) ──
                        
                        # Close previous pair's production log if exists
                        if self.last_pair:
                            old_rfids = sorted(self.last_pair)
                            await self._on_pair_removed(old_rfids[0], old_rfids[1])
                            # Turn off old relays
                            for rfid in list(self.active_outputs.keys()):
                                if rfid not in pair_key:
                                    output_info = self.active_outputs[rfid]
                                    await loop.run_in_executor(
                                        None, gpio_controller.set_output, output_info['output'], 0
                                    )
                                    logger.info(f"📴 Relay {output_info['output']} OFF (pair changed)")
                                    del self.active_outputs[rfid]
                        
                        is_new = self._is_new_pair(pair_key)
                        self._mark_pair_seen(pair_key)
                        
                        # Trigger relays for both RFIDs
                        output1 = await self._trigger_gpio(rfid1)
                        output2 = await self._trigger_gpio(rfid2)
                        
                        if output1:
                            self.active_outputs[rfid1] = {'output': output1, 'time': current_time}
                        if output2:
                            self.active_outputs[rfid2] = {'output': output2, 'time': current_time}
                        
                        if is_new:
                            # Create production log + transaction for the pair
                            await self._on_pair_detected(rfid1, rfid2, output1, output2)
                        else:
                            logger.info(f"🔄 Pair re-detected within cooldown — relay only")
                        
                        self.last_pair = pair_key
                        logger.info(f"📡 Pair detected: {rfid1[:16]}... + {rfid2[:16]}...")
                        
                    else:
                        # ── SAME PAIR STILL PRESENT — refresh timers ──
                        for rfid in [rfid1, rfid2]:
                            if rfid in self.active_outputs:
                                self.active_outputs[rfid]['time'] = current_time
                        self._mark_pair_seen(pair_key)
                    
                    self.last_read_time = current_time
                    
                elif len(detected_rfids) == 1:
                    # ═══ SINGLE TAG — NOT A PAIR, WAIT ═══
                    if self.read_count % 6 == 0:
                        logger.warning(f"⚠️ Only 1 RFID tag detected ({detected_rfids[0][:16]}...), waiting for pair...")
                    
                else:
                    # ═══ MORE THAN 2 TAGS — UNEXPECTED ═══
                    logger.warning(f"⚠️ {len(detected_rfids)} tags detected, expected exactly 2")
                    
            else:
                # ═══ NO TAGS DETECTED ═══
                if self.last_pair:
                    # Close production log for previous pair
                    old_rfids = sorted(self.last_pair)
                    await self._on_pair_removed(old_rfids[0], old_rfids[1])
                    
                    # Turn off all active relays
                    for rfid, output_info in list(self.active_outputs.items()):
                        await loop.run_in_executor(
                            None, gpio_controller.set_output, output_info['output'], 0
                        )
                        logger.info(f"📴 Relay {output_info['output']} OFF (no RFID tags)")
                    self.active_outputs.clear()
                    self.last_pair = None
                
                if self.read_count % 12 == 0:
                    logger.debug(f"RFID reader status: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error reading RFID: {e}")
            self.error_count += 1

    async def _trigger_gpio(self, rfid_number: str) -> str:
        """Trigger GPIO output for a detected RFID tag. Returns output name or None."""
        try:
            output_name = gpio_controller.get_mapped_output(rfid_number)
            if output_name:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, gpio_controller.set_output, output_name, 1
                )
                logger.info(f"⚡ Relay {output_name} ON for RFID {rfid_number[:16]}...")
                return output_name
            else:
                logger.debug(f"No relay mapping for RFID {rfid_number[:16]}...")
                return None
        except Exception as e:
            logger.error(f"Error triggering GPIO for RFID {rfid_number}: {e}")
            return None

    async def _on_pair_detected(self, rfid1: str, rfid2: str, output1: str = None, output2: str = None):
        """
        Called when a new pair of RFID tags is detected.
        Creates ONE production log and ONE transaction for both cassettes.
        """
        from app.database import SessionLocal
        from app import crud, schemas
        from app.websocket_manager import ws_manager
        import json
        
        db = SessionLocal()
        
        try:
            # Look up both cassettes
            cassette1 = crud.get_cassette_by_rfid(db, rfid1)
            cassette2 = crud.get_cassette_by_rfid(db, rfid2)
            
            if not cassette1 and not cassette2:
                logger.warning(f"⚠️ Neither RFID in pair found in Cassette Master")
                await ws_manager.broadcast_notification(
                    title="Unknown Pair",
                    message=f"Neither RFID tag is assigned to a cassette",
                    notification_type="warning"
                )
                return
            
            if not cassette1 or not cassette2:
                missing = rfid1 if not cassette1 else rfid2
                logger.warning(f"⚠️ RFID {missing[:16]}... not found in Cassette Master")
                await ws_manager.broadcast_notification(
                    title="Incomplete Pair",
                    message=f"RFID {missing[:16]}... is not assigned to any cassette",
                    notification_type="warning"
                )
                return
            
            # Check if there's already an open production log for this exact pair
            open_log = crud.get_open_production_log_by_pair(db, rfid1, rfid2)
            
            if not open_log:
                # Create new production log for the pair
                log_data = schemas.ProductionLogCreate(
                    cassette1_id=cassette1.id,
                    cassette1_code=cassette1.cassette_code,
                    rfid1=rfid1,
                    cassette2_id=cassette2.id,
                    cassette2_code=cassette2.cassette_code,
                    rfid2=rfid2,
                    relay1_output=output1,
                    relay2_output=output2,
                    from_date=datetime.now()
                )
                new_log = crud.create_production_log(db, log_data)
                log_id = new_log.id
                logger.info(f"📋 Production log #{log_id} opened for pair: {cassette1.cassette_code} + {cassette2.cassette_code}")
                
                # Create RFID transaction for the pair
                extra_info = {
                    "cassette1_desc": cassette1.desc,
                    "cassette2_desc": cassette2.desc,
                    "production_log_id": log_id
                }
                if output1:
                    extra_info["relay1_output"] = output1
                if output2:
                    extra_info["relay2_output"] = output2
                
                transaction_data = schemas.RFIDTransactionCreate(
                    rfid1=rfid1,
                    rfid2=rfid2,
                    cassette1_id=cassette1.id,
                    cassette1_code=cassette1.cassette_code,
                    cassette2_id=cassette2.id,
                    cassette2_code=cassette2.cassette_code,
                    event_type="pair_scan",
                    status="success",
                    message=f"Pair scanned: {cassette1.cassette_code} + {cassette2.cassette_code}",
                    extra_data=json.dumps(extra_info)
                )
                crud.create_rfid_transaction(db, transaction_data)
            else:
                logger.debug(f"📋 Keeping open production log #{open_log.id} for pair")
            
            # WebSocket notifications
            await ws_manager.broadcast_rfid_scan(
                rfid_number=f"{rfid1} + {rfid2}",
                cassette_code=f"{cassette1.cassette_code} + {cassette2.cassette_code}",
                status="success",
                message=f"Pair: {cassette1.cassette_code} + {cassette2.cassette_code}"
            )
            await ws_manager.broadcast_notification(
                title="Pair Scanned",
                message=f"Cassettes '{cassette1.cassette_code}' + '{cassette2.cassette_code}' detected",
                notification_type="success"
            )
            
        except Exception as e:
            logger.error(f"Error processing pair detection: {e}")
        finally:
            db.close()

    async def _on_pair_removed(self, rfid1: str, rfid2: str):
        """Called when a pair is no longer detected. Closes its production log."""
        from app.database import SessionLocal
        from app import crud
        
        db = SessionLocal()
        try:
            closed = crud.close_production_logs_by_pair(db, rfid1, rfid2)
            if closed:
                logger.info(f"📋 Production log closed for pair {rfid1[:16]}... + {rfid2[:16]}... (pair removed)")
        except Exception as e:
            logger.error(f"Error closing production log for pair: {e}")
        finally:
            db.close()

    def configure_rfid_gpio_mapping(self, rfid_number: str, output_name: str):
        """Configure RFID → relay mapping"""
        gpio_controller.configure_rfid_mapping(rfid_number, output_name)

    def stop(self):
        """Stop the background RFID reading service"""
        self.is_running = False
        logger.info("🛑 Stopping RFID Background Service...")
        gpio_controller.cleanup()

    def get_status(self):
        """Get the current status of the RFID service"""
        gpio_status = gpio_controller.get_status()
        
        active_output_details = {}
        for rfid, info in self.active_outputs.items():
            elapsed = (datetime.now() - info['time']).total_seconds()
            active_output_details[info['output']] = {
                'rfid': rfid,
                'remaining_seconds': max(0, self.output_duration - elapsed)
            }
        
        last_pair_list = sorted(self.last_pair) if self.last_pair else []
        
        return {
            "is_running": self.is_running,
            "read_interval": self.read_interval,
            "cooldown_seconds": self.cooldown_seconds,
            "total_reads": self.read_count,
            "error_count": self.error_count,
            "last_rfid": last_pair_list[0] if last_pair_list else None,
            "last_rfids": last_pair_list,
            "last_pair": last_pair_list,
            "last_read_time": self.last_read_time.isoformat() if self.last_read_time else None,
            "active_output": list(active_output_details.keys())[0] if active_output_details else None,
            "active_outputs": active_output_details,
            "output_duration": self.output_duration,
            "output_remaining_seconds": None,
            "recent_pairs_count": len(self.recent_pairs),
            "gpio": gpio_status
        }


# Global service instance
rfid_service = RFIDBackgroundService(read_interval=5)
