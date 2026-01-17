"""
RFID Reader Utility
Direct TCP connection to RFID device
"""

import socket
import logging
import config

logger = logging.getLogger(__name__)

# Import RFID Device Configuration from config.py
RFID_HOST = config.RFID_HOST
RFID_PORT = config.RFID_PORT
RFID_TIMEOUT = config.RFID_TIMEOUT



def read_rfid_tag():
    """
    Connect to RFID device, send READ command, and return the first RFID tag
    
    Returns:
        dict: {
            'success': bool,
            'rfid_number': str or None,
            'message': str
        }
    """
    tcp_socket = None
    
    try:
        # Create TCP socket
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(RFID_TIMEOUT)
        
        # Connect to RFID device
        logger.info(f"Connecting to RFID device at {RFID_HOST}:{RFID_PORT}")
        tcp_socket.connect((RFID_HOST, RFID_PORT))
        logger.info("✅ Connected to RFID device")
        
        # Send READ command with CR LF
        command = "READ\r\n"
        tcp_socket.sendall(command.encode())
        logger.info(f"📤 Sent command: {command.strip()}")
        
        # Receive response
        response = b""
        while True:
            try:
                chunk = tcp_socket.recv(1024)
                if not chunk:
                    break
                response += chunk
                # Check if we have complete response
                if b'\n' in chunk:
                    # Wait a bit more to ensure we get all tags
                    tcp_socket.settimeout(0.5)
                    try:
                        more_data = tcp_socket.recv(1024)
                        if more_data:
                            response += more_data
                    except socket.timeout:
                        break
                    break
            except socket.timeout:
                break
        
        # Decode response
        response_str = response.decode('utf-8', errors='ignore').strip()
        logger.info(f"📥 Received response: {response_str}")
        
        # Check for "NO TAG" response
        if 'NO TAG' in response_str.upper():
            return {
                'success': False,
                'rfid_number': None,
                'message': 'No RFID tag detected. Please place a tag on the reader.'
            }
        
        # Parse RFID tags (lines starting with H or E followed by hex digits)
        lines = response_str.split('\n')
        rfid_tags = []
        
        for line in lines:
            line = line.strip()
            # Match lines like H30395DFA81582E424BD7BB45 or HE2007B037AB374B16D7BE5D2
            if line and len(line) > 1 and line[0] in ['H', 'E']:
                # Check if rest is hexadecimal
                if all(c in '0123456789ABCDEFabcdef' for c in line[1:]):
                    rfid_tags.append(line)
        
        if rfid_tags:
            # Return the first RFID tag
            rfid_number = rfid_tags[0]
            logger.info(f"✅ RFID tag read successfully: {rfid_number}")
            return {
                'success': True,
                'rfid_number': rfid_number,
                'message': f'RFID tag read successfully',
                'all_tags': rfid_tags  # In case multiple tags detected
            }
        else:
            return {
                'success': False,
                'rfid_number': None,
                'message': 'Invalid response from RFID device'
            }
            
    except socket.timeout:
        logger.error("❌ RFID device connection timeout")
        return {
            'success': False,
            'rfid_number': None,
            'message': 'Connection timeout. Please check if RFID device is online.'
        }
    except ConnectionRefusedError:
        logger.error(f"❌ Connection refused to {RFID_HOST}:{RFID_PORT}")
        return {
            'success': False,
            'rfid_number': None,
            'message': f'Cannot connect to RFID device at {RFID_HOST}:{RFID_PORT}'
        }
    except Exception as e:
        logger.error(f"❌ Error reading RFID: {e}")
        return {
            'success': False,
            'rfid_number': None,
            'message': f'Error: {str(e)}'
        }
    finally:
        # Close socket
        if tcp_socket:
            try:
                tcp_socket.close()
                logger.info("🔌 Disconnected from RFID device")
            except:
                pass


def validate_rfid_format(rfid_number):
    """
    Validate RFID number format
    
    Args:
        rfid_number (str): RFID number to validate
        
    Returns:
        bool: True if valid format
    """
    if not rfid_number or len(rfid_number) < 2:
        return False
    
    # Should start with H or E
    if rfid_number[0] not in ['H', 'E']:
        return False
    
    # Rest should be hexadecimal
    return all(c in '0123456789ABCDEFabcdef' for c in rfid_number[1:])
