#!/usr/bin/env python3
"""
Keep-alive system for the Discord Football Club Bot
Prevents the bot from sleeping on hosting platforms like render.com
"""

import time
import requests
import logging
import threading
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def ping_self():
    """Ping the web server to keep it alive"""
    try:
        # Get the URL from environment or default to localhost
        base_url = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')
        
        response = requests.get(f"{base_url}/health", timeout=30)
        if response.status_code == 200:
            logger.info(f"Keep-alive ping successful at {datetime.now()}")
        else:
            logger.warning(f"Keep-alive ping returned status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Keep-alive ping failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in keep-alive: {e}")

def keep_alive():
    """Main keep-alive loop"""
    logger.info("Keep-alive system started")
    
    while True:
        try:
            # Wait 5 minutes between pings to avoid rate limiting
            time.sleep(300)  # 5 minutes
            
            # Ping the server
            ping_self()
            
        except KeyboardInterrupt:
            logger.info("Keep-alive system stopped")
            break
        except Exception as e:
            logger.error(f"Error in keep-alive loop: {e}")
            # Continue running even if there's an error
            time.sleep(60)  # Wait 1 minute before retrying

def start_keep_alive():
    """Start keep-alive in a separate thread"""
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()
    logger.info("Keep-alive thread started")
    return thread

if __name__ == "__main__":
    # For testing
    keep_alive()
