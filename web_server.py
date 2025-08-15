#!/usr/bin/env python3
"""
Simple web server for the Discord Football Club Bot
Provides keep-alive functionality and basic status page
"""

from flask import Flask, render_template, jsonify
import os
import logging
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_change_me")
    
    # Initialize database
    db = Database()
    
    @app.route('/')
    def index():
        """Main status page"""
        try:
            # Get basic statistics
            stats = {
                'status': 'Online',
                'uptime': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'version': '1.0.0'
            }
            
            return render_template('index.html', stats=stats)
        except Exception as e:
            logger.error(f"Error in index route: {e}")
            return render_template('index.html', stats={'status': 'Error', 'uptime': 'Unknown', 'version': '1.0.0'})
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'football-bot'
        })
    
    @app.route('/api/status')
    def api_status():
        """API status endpoint"""
        try:
            return jsonify({
                'bot_status': 'online',
                'database_status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'features': [
                    'Club Management',
                    'Player Management', 
                    'Match Scheduling',
                    'Transfer System',
                    'Statistics',
                    'Rate Limiting Protection'
                ]
            })
        except Exception as e:
            logger.error(f"Error in status API: {e}")
            return jsonify({
                'bot_status': 'error',
                'database_status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return render_template('index.html', stats={'status': 'Page Not Found', 'uptime': 'N/A', 'version': '1.0.0'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return render_template('index.html', stats={'status': 'Internal Error', 'uptime': 'N/A', 'version': '1.0.0'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
