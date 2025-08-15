#!/usr/bin/env python3
"""
Database management for the Football Club Bot
SQLite database with comprehensive football management features
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "football_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize the database with all required tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clubs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS clubs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        budget REAL NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(guild_id, name)
                    )
                ''')
                
                # Players table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        club_id INTEGER,
                        value REAL NOT NULL DEFAULT 0,
                        position TEXT DEFAULT 'Forward',
                        age INTEGER DEFAULT 25,
                        contract_end DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (club_id) REFERENCES clubs (id) ON DELETE SET NULL,
                        UNIQUE(guild_id, name)
                    )
                ''')
                
                # Matches table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        team1_id INTEGER NOT NULL,
                        team2_id INTEGER NOT NULL,
                        datetime TEXT NOT NULL,
                        description TEXT DEFAULT 'League Match',
                        reminder_sent BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Transfer history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transfers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        player_name TEXT NOT NULL,
                        from_club TEXT,
                        to_club TEXT,
                        fee REAL NOT NULL DEFAULT 0,
                        admin_id INTEGER NOT NULL,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Bot settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        setting_name TEXT NOT NULL,
                        setting_value TEXT,
                        UNIQUE(guild_id, setting_name)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    # Club Management Methods
    
    def create_club(self, guild_id: int, name: str, budget: float) -> bool:
        """Create a new club"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO clubs (guild_id, name, budget) VALUES (?, ?, ?)",
                    (guild_id, name, budget)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Club already exists
        except Exception as e:
            logger.error(f"Error creating club: {e}")
            return False
    
    def delete_club(self, guild_id: int, name: str) -> bool:
        """Delete a club and set all its players as free agents"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get club ID
                cursor.execute(
                    "SELECT id FROM clubs WHERE guild_id = ? AND name = ?",
                    (guild_id, name)
                )
                club = cursor.fetchone()
                
                if not club:
                    return False
                
                # Set players as free agents
                cursor.execute(
                    "UPDATE players SET club_id = NULL WHERE club_id = ?",
                    (club['id'],)
                )
                
                # Delete the club
                cursor.execute(
                    "DELETE FROM clubs WHERE id = ?",
                    (club['id'],)
                )
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting club: {e}")
            return False
    
    def get_clubs(self, guild_id: int) -> List[Dict]:
        """Get all clubs in a guild"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM clubs WHERE guild_id = ? ORDER BY budget DESC",
                    (guild_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting clubs: {e}")
            return []
    
    def update_club_budget(self, guild_id: int, name: str, budget: float) -> bool:
        """Update a club's budget"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE clubs SET budget = ? WHERE guild_id = ? AND name = ?",
                    (budget, guild_id, name)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating club budget: {e}")
            return False
    
    def get_club_by_name(self, guild_id: int, name: str) -> Optional[Dict]:
        """Get a club by name"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM clubs WHERE guild_id = ? AND name = ?",
                    (guild_id, name)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting club: {e}")
            return None
    
    # Player Management Methods
    
    def add_player(self, guild_id: int, name: str, club_name: str, value: float, position: str = "Forward", age: int = 25) -> bool:
        """Add a player to a club"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get club ID
                club = self.get_club_by_name(guild_id, club_name)
                if not club:
                    return False
                
                # Add contract end date (2 years from now)
                contract_end = (datetime.now() + timedelta(days=730)).strftime('%Y-%m-%d')
                
                cursor.execute(
                    "INSERT INTO players (guild_id, name, club_id, value, position, age, contract_end) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (guild_id, name, club['id'], value, position, age, contract_end)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Player already exists
        except Exception as e:
            logger.error(f"Error adding player: {e}")
            return False
    
    def remove_player(self, guild_id: int, name: str) -> bool:
        """Remove a player"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM players WHERE guild_id = ? AND name = ?",
                    (guild_id, name)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing player: {e}")
            return False
    
    def update_player_value(self, guild_id: int, name: str, value: float) -> bool:
        """Update a player's value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET value = ? WHERE guild_id = ? AND name = ?",
                    (value, guild_id, name)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating player value: {e}")
            return False
    
    def transfer_player(self, guild_id: int, player_name: str, from_club: str, to_club: str, transfer_fee: float) -> bool:
        """Transfer a player between clubs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get clubs
                from_club_data = self.get_club_by_name(guild_id, from_club)
                to_club_data = self.get_club_by_name(guild_id, to_club)
                
                if not from_club_data or not to_club_data:
                    return False
                
                # Check if destination club has enough budget
                if to_club_data['budget'] < transfer_fee:
                    return False
                
                # Update player's club
                cursor.execute(
                    "UPDATE players SET club_id = ? WHERE guild_id = ? AND name = ? AND club_id = ?",
                    (to_club_data['id'], guild_id, player_name, from_club_data['id'])
                )
                
                if cursor.rowcount == 0:
                    return False
                
                # Update club budgets
                cursor.execute(
                    "UPDATE clubs SET budget = budget + ? WHERE id = ?",
                    (transfer_fee, from_club_data['id'])
                )
                cursor.execute(
                    "UPDATE clubs SET budget = budget - ? WHERE id = ?",
                    (transfer_fee, to_club_data['id'])
                )
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error transferring player: {e}")
            return False
    
    def get_club_players(self, guild_id: int, club_name: str) -> List[Dict]:
        """Get all players in a club"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.*, c.name as club_name 
                    FROM players p 
                    LEFT JOIN clubs c ON p.club_id = c.id 
                    WHERE p.guild_id = ? AND c.name = ?
                    ORDER BY p.value DESC
                ''', (guild_id, club_name))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting club players: {e}")
            return []
    
    def get_all_players(self, guild_id: int) -> List[Dict]:
        """Get all players in a guild"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.*, c.name as club_name 
                    FROM players p 
                    LEFT JOIN clubs c ON p.club_id = c.id 
                    WHERE p.guild_id = ?
                    ORDER BY p.value DESC
                ''', (guild_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all players: {e}")
            return []
    
    def get_player_count(self, club_id: int) -> int:
        """Get the number of players in a club"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM players WHERE club_id = ?",
                    (club_id,)
                )
                return cursor.fetchone()['count']
        except Exception as e:
            logger.error(f"Error getting player count: {e}")
            return 0
    
    # Match Management Methods
    
    def create_match(self, guild_id: int, team1_id: int, team2_id: int, datetime_str: str, description: str) -> Optional[int]:
        """Create a new match"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO matches (guild_id, team1_id, team2_id, datetime, description) VALUES (?, ?, ?, ?, ?)",
                    (guild_id, team1_id, team2_id, datetime_str, description)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return None
    
    def get_upcoming_matches(self, guild_id: Optional[int] = None) -> List[Dict]:
        """Get upcoming matches"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                if guild_id:
                    cursor.execute(
                        "SELECT * FROM matches WHERE guild_id = ? AND datetime > ? ORDER BY datetime ASC",
                        (guild_id, current_time)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM matches WHERE datetime > ? ORDER BY datetime ASC",
                        (current_time,)
                    )
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting upcoming matches: {e}")
            return []
    
    def mark_reminder_sent(self, match_id: int):
        """Mark that a reminder has been sent for a match"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE matches SET reminder_sent = TRUE WHERE id = ?",
                    (match_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error marking reminder sent: {e}")
    
    # Transfer History Methods
    
    def log_transfer(self, guild_id: int, player_name: str, from_club: str, to_club: str, fee: float, admin_id: int):
        """Log a transfer to history"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO transfers (guild_id, player_name, from_club, to_club, fee, admin_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (guild_id, player_name, from_club, to_club, fee, admin_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging transfer: {e}")
    
    def get_transfer_history(self, guild_id: int, limit: int = 20) -> List[Dict]:
        """Get transfer history"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM transfers WHERE guild_id = ? ORDER BY date DESC LIMIT ?",
                    (guild_id, limit)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting transfer history: {e}")
            return []
    
    # Statistics Methods
    
    def get_club_stats(self, guild_id: int, club_name: str) -> Optional[Dict]:
        """Get comprehensive club statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get club basic info
                club = self.get_club_by_name(guild_id, club_name)
                if not club:
                    return None
                
                # Get player statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as player_count,
                        COALESCE(SUM(value), 0) as total_value,
                        COALESCE(AVG(value), 0) as avg_value,
                        COALESCE(MAX(value), 0) as highest_value
                    FROM players 
                    WHERE club_id = ?
                ''', (club['id'],))
                
                stats = dict(cursor.fetchone())
                
                # Get most valuable player
                cursor.execute(
                    "SELECT name FROM players WHERE club_id = ? ORDER BY value DESC LIMIT 1",
                    (club['id'],)
                )
                most_valuable = cursor.fetchone()
                stats['most_valuable'] = most_valuable['name'] if most_valuable else 'None'
                
                # Get transfer counts
                cursor.execute(
                    "SELECT COUNT(*) as transfers_in FROM transfers WHERE guild_id = ? AND to_club = ?",
                    (guild_id, club_name)
                )
                stats['transfers_in'] = cursor.fetchone()['transfers_in']
                
                cursor.execute(
                    "SELECT COUNT(*) as transfers_out FROM transfers WHERE guild_id = ? AND from_club = ?",
                    (guild_id, club_name)
                )
                stats['transfers_out'] = cursor.fetchone()['transfers_out']
                
                # Combine with club data
                result = {**club, **stats}
                return result
                
        except Exception as e:
            logger.error(f"Error getting club stats: {e}")
            return None
    
    def get_top_players(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get top players by value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.*, c.name as club_name 
                    FROM players p 
                    LEFT JOIN clubs c ON p.club_id = c.id 
                    WHERE p.guild_id = ?
                    ORDER BY p.value DESC 
                    LIMIT ?
                ''', (guild_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting top players: {e}")
            return []
    
    def get_richest_clubs(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get richest clubs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.*, COUNT(p.id) as player_count
                    FROM clubs c
                    LEFT JOIN players p ON c.id = p.club_id
                    WHERE c.guild_id = ?
                    GROUP BY c.id
                    ORDER BY c.budget DESC
                    LIMIT ?
                ''', (guild_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting richest clubs: {e}")
            return []
    
    def get_server_stats(self, guild_id: int) -> Dict:
        """Get comprehensive server statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total clubs
                cursor.execute("SELECT COUNT(*) as count FROM clubs WHERE guild_id = ?", (guild_id,))
                stats['total_clubs'] = cursor.fetchone()['count']
                
                # Total players
                cursor.execute("SELECT COUNT(*) as count FROM players WHERE guild_id = ?", (guild_id,))
                stats['total_players'] = cursor.fetchone()['count']
                
                # Upcoming matches
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                cursor.execute(
                    "SELECT COUNT(*) as count FROM matches WHERE guild_id = ? AND datetime > ?",
                    (guild_id, current_time)
                )
                stats['upcoming_matches'] = cursor.fetchone()['count']
                
                # Total transfers
                cursor.execute("SELECT COUNT(*) as count FROM transfers WHERE guild_id = ?", (guild_id,))
                stats['total_transfers'] = cursor.fetchone()['count']
                
                # Total market value
                cursor.execute("SELECT COALESCE(SUM(value), 0) as total FROM players WHERE guild_id = ?", (guild_id,))
                stats['total_value'] = cursor.fetchone()['total']
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting server stats: {e}")
            return {
                'total_clubs': 0,
                'total_players': 0,
                'upcoming_matches': 0,
                'total_transfers': 0,
                'total_value': 0
            }
    
    # Utility Methods
    
    def reset_all_data(self, guild_id: int):
        """Reset all data for a guild"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete in correct order to handle foreign keys
                cursor.execute("DELETE FROM transfers WHERE guild_id = ?", (guild_id,))
                cursor.execute("DELETE FROM matches WHERE guild_id = ?", (guild_id,))
                cursor.execute("DELETE FROM players WHERE guild_id = ?", (guild_id,))
                cursor.execute("DELETE FROM clubs WHERE guild_id = ?", (guild_id,))
                cursor.execute("DELETE FROM bot_settings WHERE guild_id = ?", (guild_id,))
                
                conn.commit()
                logger.info(f"All data reset for guild {guild_id}")
                
        except Exception as e:
            logger.error(f"Error resetting all data: {e}")
            raise
    
    def close(self):
        """Close database connection (if needed)"""
        # SQLite connections are closed automatically when using context managers
        pass
