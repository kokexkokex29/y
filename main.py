#!/usr/bin/env python3
"""
Main entry point for the Discord Football Club Management Bot
Starts both the bot and the web server with keep-alive functionality
"""

import os
import asyncio
import threading
import logging
from bot import start_bot
from web_server import create_app
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create Flask app for gunicorn
app = create_app()

def run_discord_bot():
    """Run the Discord bot in a separate thread"""
    try:
        asyncio.run(start_bot())
    except Exception as e:
        logger.error(f"Discord bot error: {e}")

# Start background services when module is imported
if os.getenv('DISCORD_TOKEN'):  # Only start if token is available
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()
    logger.info("Discord bot started in background")
    
    # Start keep-alive system
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("Keep-alive system started")

async def main():
    """Main function for direct execution"""
    logger.info("Starting Football Club Management Bot...")
    
    # Start web server in a separate thread
    def run_web_server():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("Web server started on port 5000")
    
    # Start keep-alive system
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("Keep-alive system started")
    
    # Start the Discord bot
    await start_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
