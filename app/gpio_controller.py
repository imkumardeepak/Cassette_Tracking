"""
GPIO Controller for Cygnus Board
Controls digital outputs based on RFID scans
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ==========================
# GPIO Mapping for Cygnus Board
# ==========================

# Digital Outputs (DO0-DO3)
GPIO_OUTPUTS = {
    "DO0": 403,  # GPIO 18 → 385 + 18 = 403
    "DO1": 404,  # GPIO 19 → 385 + 19 = 404
    "DO2": 378,  # PM_GPIO 4 → 374 + 4 = 378
    "DO3": 382,  # PM_GPIO 8 → 374 + 8 = 382
}

# Digital Inputs (DI0-DI2) - for future use
GPIO_INPUTS = {
    "DI0": 417,  # GPIO 32 → 385 + 32 = 417
    "DI1": 418,  # GPIO 33 → 385 + 33 = 418
    "DI2": 420,  # GPIO 35 → 385 + 35 = 420
}


class GPIOController:
    """
    GPIO Controller for Cygnus Board
    Maps RFID numbers to GPIO outputs
    """
    
    def __init__(self):
        self.rfid_to_output_map: Dict[str, str] = {}  # RFID number → Output name (DO0, DO1, etc.)
        self.output_states: Dict[str, int] = {name: 0 for name in GPIO_OUTPUTS}
        self.initialized = False
        self.simulation_mode = True  # Set to False when running on actual hardware
        
    def initialize(self):
        """Initialize all GPIO pins"""
        if self.initialized:
            return
            
        logger.info("🔧 Initializing GPIO Controller...")
        
        # Check if running on Linux with GPIO support
        if not os.path.exists("/sys/class/gpio"):
            logger.warning("⚠️ GPIO not available - running in simulation mode")
            self.simulation_mode = True
            self.initialized = True
            return
            
        self.simulation_mode = False
        
        try:
            # Export and configure all output pins
            for name, pin in GPIO_OUTPUTS.items():
                self._export_gpio(pin)
                self._set_direction(pin, "out")
                self._write_gpio(pin, 0)  # Initialize to LOW
                logger.info(f"✅ Initialized {name} (GPIO {pin}) as OUTPUT")
                
            self.initialized = True
            logger.info("✅ GPIO Controller initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize GPIO: {e}")
            self.simulation_mode = True
            self.initialized = True
    
    def _export_gpio(self, pin: int):
        """Export GPIO so it becomes available in /sys/class/gpio/"""
        if not os.path.exists(f"/sys/class/gpio/gpio{pin}"):
            try:
                with open("/sys/class/gpio/export", "w") as f:
                    f.write(str(pin))
            except Exception as e:
                logger.debug(f"GPIO {pin} export: {e}")
    
    def _set_direction(self, pin: int, direction: str):
        """Set GPIO direction: 'in' or 'out'"""
        try:
            with open(f"/sys/class/gpio/gpio{pin}/direction", "w") as f:
                f.write(direction)
        except Exception as e:
            logger.error(f"Failed to set GPIO {pin} direction: {e}")
            raise
    
    def _read_gpio(self, pin: int) -> int:
        """Read GPIO input value and return 0/1"""
        try:
            with open(f"/sys/class/gpio/gpio{pin}/value", "r") as f:
                return int(f.read().strip())
        except Exception as e:
            logger.error(f"Failed to read GPIO {pin}: {e}")
            return 0
    
    def _write_gpio(self, pin: int, value: int):
        """Write 1 or 0 to output"""
        try:
            with open(f"/sys/class/gpio/gpio{pin}/value", "w") as f:
                f.write("1" if value else "0")
        except Exception as e:
            logger.error(f"Failed to write GPIO {pin}: {e}")
            raise
    
    def configure_rfid_mapping(self, rfid_number: str, output_name: str):
        """
        Map an RFID number to a specific output (in-memory mapping)
        Note: For persistent mapping, use the gpio_output field in CassetteMaster
        
        Args:
            rfid_number: The RFID tag number
            output_name: Output name (DO0, DO1, DO2, DO3)
        """
        if output_name not in GPIO_OUTPUTS:
            raise ValueError(f"Invalid output name: {output_name}. Valid options: {list(GPIO_OUTPUTS.keys())}")
            
        self.rfid_to_output_map[rfid_number] = output_name
        logger.info(f"🔗 Mapped RFID {rfid_number} → {output_name}")
    
    def load_mappings_from_db(self):
        """
        Load RFID-GPIO mappings from database (CassetteMaster table)
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
            
            logger.info(f"📂 Loaded {len(self.rfid_to_output_map)} RFID-GPIO mappings from database")
            return self.rfid_to_output_map.copy()
            
        except Exception as e:
            logger.error(f"Error loading mappings from database: {e}")
            return {}
        finally:
            db.close()
    
    def get_output_for_rfid(self, rfid_number: str) -> str:
        """
        Get the GPIO output for a given RFID number
        First checks in-memory cache, then loads from database if not found
        
        Args:
            rfid_number: The RFID tag number
            
        Returns:
            Output name (DO0, DO1, DO2, DO3) or None
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
            logger.error(f"Error getting GPIO mapping for RFID: {e}")
        finally:
            db.close()
        
        return None
    
    def set_output(self, output_name: str, value: int) -> bool:
        """
        Set a specific output HIGH or LOW
        
        Args:
            output_name: Output name (DO0, DO1, DO2, DO3)
            value: 1 for HIGH, 0 for LOW
            
        Returns:
            True if successful, False otherwise
        """
        if output_name not in GPIO_OUTPUTS:
            logger.error(f"Invalid output: {output_name}")
            return False
            
        pin = GPIO_OUTPUTS[output_name]
        
        if self.simulation_mode:
            logger.info(f"🔌 [SIMULATION] {output_name} (GPIO {pin}) → {'HIGH' if value else 'LOW'}")
            self.output_states[output_name] = value
            return True
            
        try:
            self._write_gpio(pin, value)
            self.output_states[output_name] = value
            logger.info(f"🔌 {output_name} (GPIO {pin}) → {'HIGH' if value else 'LOW'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set {output_name}: {e}")
            return False
    
    def on_rfid_scanned(self, rfid_number: str) -> Optional[str]:
        """
        Handle RFID scan - set corresponding output to HIGH
        
        Args:
            rfid_number: The scanned RFID number
            
        Returns:
            The output name that was triggered, or None if no mapping exists
        """
        if not self.initialized:
            self.initialize()
            
        # Check if this RFID has a mapping
        if rfid_number in self.rfid_to_output_map:
            output_name = self.rfid_to_output_map[rfid_number]
            
            # Reset all outputs first (optional - remove if you want multiple outputs active)
            # for name in GPIO_OUTPUTS:
            #     self.set_output(name, 0)
            
            # Set the mapped output to HIGH
            success = self.set_output(output_name, 1)
            
            if success:
                logger.info(f"📡 RFID {rfid_number} triggered {output_name} → HIGH")
                return output_name
        else:
            logger.debug(f"No GPIO mapping for RFID: {rfid_number}")
            
        return None
    
    def reset_all_outputs(self):
        """Reset all outputs to LOW"""
        for name in GPIO_OUTPUTS:
            self.set_output(name, 0)
        logger.info("🔄 All outputs reset to LOW")
    
    def get_status(self) -> Dict:
        """Get current GPIO status"""
        return {
            "initialized": self.initialized,
            "simulation_mode": self.simulation_mode,
            "outputs": self.output_states.copy(),
            "rfid_mappings": self.rfid_to_output_map.copy(),
            "available_outputs": list(GPIO_OUTPUTS.keys()),
        }
    
    def cleanup(self):
        """Cleanup GPIO on shutdown"""
        logger.info("🛑 Cleaning up GPIO...")
        self.reset_all_outputs()


# Global GPIO controller instance
gpio_controller = GPIOController()
