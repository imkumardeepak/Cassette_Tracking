"""
Modbus RTU Relay Controller for Cygnus Board
Controls relay outputs via RS-485 Modbus RTU protocol

Modbus Register Map:
  Address 0x0002 | RELAY_STATE | Read: FC 0x01, Write: FC 0x05
  Relay Outputs 1-10 (bitwise: bit 0 = Relay1)
  
  RELAY1 -> coil address 0x0002
  RELAY2 -> coil address 0x0003
  ...
  RELAY8 -> coil address 0x0009
"""

import os
import logging
import platform
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ==========================
# Relay Output Mapping (Modbus Coils)
# ==========================
# Base coil address for relays (from Modbus register map)
RELAY_BASE_ADDRESS = 0x0002

# 8 Relay outputs: RELAY1-RELAY8
# Each relay maps to a sequential coil address starting from RELAY_BASE_ADDRESS
RELAY_OUTPUTS = {
    f"RELAY{i}": RELAY_BASE_ADDRESS + (i - 1) for i in range(1, 9)
}
# Result: {"RELAY1": 2, "RELAY2": 3, "RELAY3": 4, ..., "RELAY8": 9}


class RelayController:
    """
    Modbus RTU Relay Controller
    Controls relay outputs via RS-485 serial connection (Cygnus Board)
    
    Communication:
      - Protocol: Modbus RTU over RS-485
      - Serial Port: /dev/ttyHS2 (configurable)
      - Baud Rate: 9600 (configurable)
      - Read Relay: Function Code 0x01 (Read Coils)
      - Write Relay: Function Code 0x05 (Write Single Coil)
    """
    
    def __init__(self):
        self.client = None
        self.rfid_to_output_map: Dict[str, str] = {}  # RFID number -> Relay name
        self.output_states: Dict[str, int] = {name: 0 for name in RELAY_OUTPUTS}
        self.initialized = False
        self.simulation_mode = True
        self.slave_id = 1
        
    def initialize(self):
        """Initialize Modbus RTU connection to relay board"""
        if self.initialized:
            return
            
        logger.info("🔧 Initializing Modbus RTU Relay Controller...")
        
        import config
        
        # Check if running on Linux with serial port available
        is_linux = platform.system() == "Linux"
        serial_port_exists = os.path.exists(config.MODBUS_PORT)
        
        if not is_linux or not serial_port_exists:
            logger.warning(f"⚠️ Modbus serial port ({config.MODBUS_PORT}) not available - running in simulation mode")
            self.simulation_mode = True
            self.initialized = True
            return
            
        self.simulation_mode = False
        self.slave_id = config.MODBUS_SLAVE_ID
        
        try:
            from pymodbus.client import ModbusSerialClient
            
            self.client = ModbusSerialClient(
                port=config.MODBUS_PORT,
                baudrate=config.MODBUS_BAUDRATE,
                parity=config.MODBUS_PARITY,
                stopbits=config.MODBUS_STOPBITS,
                bytesize=config.MODBUS_BYTESIZE,
                timeout=config.MODBUS_TIMEOUT
            )
            
            connected = self.client.connect()
            if connected:
                logger.info(f"✅ Connected to Modbus relay board on {config.MODBUS_PORT}")
                logger.info(f"   Slave ID: {self.slave_id}, Baud: {config.MODBUS_BAUDRATE}, Parity: {config.MODBUS_PARITY}")
                
                # Read current relay states from device
                self.read_relay_states()
                
                # Reset all relays on init
                self.reset_all_outputs()
                self.initialized = True
                logger.info(f"✅ Relay Controller initialized ({len(RELAY_OUTPUTS)} outputs: RELAY1-RELAY8)")
            else:
                logger.error(f"❌ Failed to connect to Modbus device on {config.MODBUS_PORT}")
                self.simulation_mode = True
                self.initialized = True
                
        except ImportError:
            logger.error("❌ pymodbus not installed. Run: pip install pymodbus pyserial")
            self.simulation_mode = True
            self.initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Modbus: {e}")
            self.simulation_mode = True
            self.initialized = True
    
    def configure_rfid_mapping(self, rfid_number: str, output_name: str):
        """
        Map an RFID number to a specific relay output (in-memory)
        Note: For persistent mapping, use the gpio_output field in CassetteMaster
        
        Args:
            rfid_number: The RFID tag number
            output_name: Relay name (RELAY1-RELAY8)
        """
        if output_name not in RELAY_OUTPUTS:
            raise ValueError(f"Invalid relay: {output_name}. Valid options: {list(RELAY_OUTPUTS.keys())}")
            
        self.rfid_to_output_map[rfid_number] = output_name
        logger.info(f"🔗 Mapped RFID {rfid_number} → {output_name}")
    
    def load_mappings_from_db(self):
        """
        Load RFID-Relay mappings from database (CassetteMaster table)
        Returns the mapping dictionary
        """
        from app.database import SessionLocal
        from app import models
        
        db = SessionLocal()
        try:
            # Get all cassettes with both rfid_number and gpio_output assigned
            cassettes = db.query(models.CassetteMaster).filter(
                models.CassetteMaster.rfid_number.isnot(None),
                models.CassetteMaster.gpio_output.isnot(None)
            ).all()
            
            # Clear existing in-memory mappings and load from DB
            self.rfid_to_output_map.clear()
            
            for cassette in cassettes:
                if cassette.rfid_number and cassette.gpio_output:
                    self.rfid_to_output_map[cassette.rfid_number] = cassette.gpio_output
                    logger.debug(f"Loaded mapping: {cassette.rfid_number} → {cassette.gpio_output}")
            
            logger.info(f"📂 Loaded {len(self.rfid_to_output_map)} RFID-Relay mappings from database")
            return self.rfid_to_output_map.copy()
            
        except Exception as e:
            logger.error(f"Error loading mappings from database: {e}")
            return {}
        finally:
            db.close()
    
    def get_output_for_rfid(self, rfid_number: str) -> Optional[str]:
        """
        Get the relay output for a given RFID number
        First checks in-memory cache, then loads from database if not found
        
        Args:
            rfid_number: The RFID tag number
            
        Returns:
            Relay name (RELAY1-RELAY8) or None
        """
        # Check in-memory cache first
        if rfid_number in self.rfid_to_output_map:
            return self.rfid_to_output_map[rfid_number]
        
        # Try to load from database
        from app.database import SessionLocal
        from app import models
        
        db = SessionLocal()
        try:
            cassette = db.query(models.CassetteMaster).filter(
                models.CassetteMaster.rfid_number == rfid_number
            ).first()
            
            if cassette and cassette.gpio_output:
                # Cache the mapping
                self.rfid_to_output_map[rfid_number] = cassette.gpio_output
                return cassette.gpio_output
                
        except Exception as e:
            logger.error(f"Error getting relay mapping for RFID: {e}")
        finally:
            db.close()
        
        return None
    
    def set_output(self, output_name: str, value: int) -> bool:
        """
        Set a relay output ON or OFF via Modbus coil write (FC 0x05)
        
        Args:
            output_name: Relay name (RELAY1-RELAY8)
            value: 1 for ON, 0 for OFF
            
        Returns:
            True if successful, False otherwise
        """
        if output_name not in RELAY_OUTPUTS:
            logger.error(f"Invalid relay: {output_name}. Valid: {list(RELAY_OUTPUTS.keys())}")
            return False
            
        coil_address = RELAY_OUTPUTS[output_name]
        
        if self.simulation_mode:
            logger.info(f"🔌 [SIMULATION] {output_name} (coil 0x{coil_address:04X}) → {'ON' if value else 'OFF'}")
            self.output_states[output_name] = value
            return True
            
        try:
            # Write single coil (FC 0x05)
            result = self.client.write_coil(
                address=coil_address,
                value=bool(value),
                slave=self.slave_id
            )
            
            if result.isError():
                logger.error(f"Modbus error setting {output_name}: {result}")
                return False
                
            self.output_states[output_name] = value
            logger.info(f"🔌 {output_name} (coil 0x{coil_address:04X}) → {'ON' if value else 'OFF'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set {output_name}: {e}")
            return False
    
    def read_relay_states(self) -> Dict[str, int]:
        """
        Read current state of all relays from the device via Modbus (FC 0x01)
        
        Returns:
            Dictionary of relay states {RELAY1: 0/1, RELAY2: 0/1, ...}
        """
        if self.simulation_mode:
            return self.output_states.copy()
            
        try:
            # Read coils starting from base address (FC 0x01)
            result = self.client.read_coils(
                address=RELAY_BASE_ADDRESS,
                count=len(RELAY_OUTPUTS),
                slave=self.slave_id
            )
            
            if result.isError():
                logger.error(f"Modbus error reading relays: {result}")
                return self.output_states.copy()
                
            # Update internal state from device
            for i, name in enumerate(RELAY_OUTPUTS):
                self.output_states[name] = 1 if result.bits[i] else 0
                
            logger.debug(f"Read relay states: {self.output_states}")
            return self.output_states.copy()
            
        except Exception as e:
            logger.error(f"Error reading relay states: {e}")
            return self.output_states.copy()
    
    def on_rfid_scanned(self, rfid_number: str) -> Optional[str]:
        """
        Handle RFID scan - set corresponding relay to ON
        
        Args:
            rfid_number: The scanned RFID number
            
        Returns:
            The relay name that was triggered, or None if no mapping exists
        """
        if not self.initialized:
            self.initialize()
            
        # Check if this RFID has a mapping
        output_name = self.get_output_for_rfid(rfid_number)
        if output_name:
            success = self.set_output(output_name, 1)
            if success:
                logger.info(f"📡 RFID {rfid_number} triggered {output_name} → ON")
                return output_name
        else:
            logger.debug(f"No relay mapping for RFID: {rfid_number}")
            
        return None
    
    def reset_all_outputs(self):
        """Turn OFF all relay outputs"""
        for name in RELAY_OUTPUTS:
            self.set_output(name, 0)
        logger.info("🔄 All relays reset to OFF")
    
    def get_status(self) -> Dict:
        """Get current relay controller status"""
        return {
            "initialized": self.initialized,
            "simulation_mode": self.simulation_mode,
            "connection_type": "Modbus RTU (RS-485)",
            "slave_id": self.slave_id,
            "outputs": self.output_states.copy(),
            "rfid_mappings": self.rfid_to_output_map.copy(),
            "available_outputs": list(RELAY_OUTPUTS.keys()),
        }
    
    def cleanup(self):
        """Cleanup on shutdown - turn off all relays and close connection"""
        logger.info("🛑 Cleaning up Modbus relay controller...")
        self.reset_all_outputs()
        if self.client:
            try:
                self.client.close()
                logger.info("🔌 Modbus connection closed")
            except:
                pass


# Global controller instance (same variable name for backward compatibility)
gpio_controller = RelayController()
