import sqlite3
import os
from pathlib import Path
import logging
from .logger import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger("bot.db")

class SettingsDatabaseManager:
    """
    This class manages server settings in the database.
    """
    
    def __init__(self, db_path="data/settings.db"):
        """
        Initialize the database manager

        Args:
            db_path (str): The path to the database file
        """

        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Database manager initialized with database at {db_path}")
    
    def _init_db(self):
        """Initialize the database, create necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create server settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            server_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            role_id INTEGER,
            post_time TEXT DEFAULT '00:00',
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.debug("Database tables initialized")
    
    def get_server_settings(self, server_id):
        """Get the settings for a specific server
        
        Args:
            server_id (int): Discord server ID
            
            Returns:
                dict: server settings, return None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT channel_id, role_id, post_time, timezone FROM server_settings WHERE server_id = ?",
            (server_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            logger.debug(f"Server {server_id} settings: {result}")
            return {"server_id": server_id,
                    "channel_id": result[0],
                    "role_id": result[1],
                    "post_time": result[2],
                    "timezone": result[3]}
        return None
    
    def set_server_settings(self, server_id, channel_id, role_id=None, post_time="00:00", timezone="UTC"):
        """Set or update server settings
        
        Args:
            server_id (int): Discord server ID
            channel_id (int): The channel ID to send the daily challenge
            role_id (int, optional): The role ID to mention
            post_time (str, optional): The time to send the daily challenge, format "HH:MM"
            timezone (str, optional): The timezone name
            
        Returns:
            bool: return True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO server_settings (server_id, channel_id, role_id, post_time, timezone)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(server_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    role_id = excluded.role_id,
                    post_time = excluded.post_time,
                    timezone = excluded.timezone,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (server_id, channel_id, role_id, post_time, timezone)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting server settings: {e}")
            return False
        finally:
            logger.debug(f"Server {server_id} settings updated: ({channel_id}, {role_id}, {post_time}, {timezone})")
            conn.close()
    
    def set_channel(self, server_id, channel_id):
        """Update the server notification channel
        
        Args:
            server_id (int): Discord server ID
            channel_id (int): The channel ID
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                channel_id,
                settings.get("role_id"),
                settings.get("post_time", "00:00"),
                settings.get("timezone", "UTC")
            )
        else:
            return self.set_server_settings(server_id, channel_id)
    
    def set_role(self, server_id, role_id):
        """Update the server notification role
        
        Args:
            server_id (int): Discord server ID
            role_id (int): The role ID
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                settings.get("channel_id"),
                role_id,
                settings.get("post_time", "00:00"),
                settings.get("timezone", "UTC")
            )
        return False  # return False if server settings not found
    
    def set_post_time(self, server_id, post_time):
        """Update the server notification time
        
        Args:
            server_id (int): Discord server ID
            post_time (str): The time to send the daily challenge, format "HH:MM"
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                settings.get("channel_id"),
                settings.get("role_id"),
                post_time,
                settings.get("timezone", "UTC")
            )
        return False  # return False if server settings not found
    
    def set_timezone(self, server_id, timezone):
        """Update the server notification timezone
        
        Args:
            server_id (int): Discord server ID
            timezone (str): The timezone name
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                settings.get("channel_id"),
                settings.get("role_id"),
                settings.get("post_time", "00:00"),
                timezone
            )
        return False  # return False if server settings not found
    
    def get_all_servers(self):
        """Get all servers with settings
        
        Returns:
            list: A list of dictionaries containing all server settings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT server_id, channel_id, role_id, post_time, timezone FROM server_settings"
        )
        results = cursor.fetchall()
        conn.close()
        
        servers = []
        for row in results:
            servers.append({
                "server_id": row[0],
                "channel_id": row[1],
                "role_id": row[2],
                "post_time": row[3],
                "timezone": row[4]
            })
        
        return servers
    
    def delete_server_settings(self, server_id):
        """Delete server settings
        
        Args:
            server_id (int): Discord server ID
            
        Returns:
            bool: return True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM server_settings WHERE server_id = ?", (server_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting server settings: {e}")
            return False
        finally:
            conn.close()

if __name__ == "__main__":
    # Example usage
    db_manager = SettingsDatabaseManager()
    db_manager.set_server_settings(123456789, 987654321, role_id=111222333, post_time="12:00", timezone="UTC")
    settings = db_manager.get_server_settings(123456789)
    logger.debug(settings)
    db_manager.delete_server_settings(123456789)  # Delete settings for server ID 123456789 