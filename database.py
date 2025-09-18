import asyncio
import asyncpg
import json
import os
from typing import List, Optional
from datetime import datetime, timedelta

class Database:
    def __init__(self, config: dict):
        self.config = config
        self.pool = None

    async def connect(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                min_size=5,
                max_size=20
            )
            print("✅ Connected to PostgreSQL database")
            await self._create_tables()
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            print("📊 Database connection closed")

    async def _create_tables(self):
        """Create necessary tables if they don't exist."""
        async with self.pool.acquire() as conn:
            # Servers table to track which servers the bot is in
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    guild_id BIGINT PRIMARY KEY,
                    guild_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Shuffleable roles table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS shuffleable_roles (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT REFERENCES servers(guild_id) ON DELETE CASCADE,
                    role_id BIGINT NOT NULL,
                    role_name VARCHAR(255) NOT NULL,
                    added_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, role_id)
                )
            ''')

            # Cooldowns table to track shuffle cooldowns per server
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS shuffle_cooldowns (
                    guild_id BIGINT PRIMARY KEY REFERENCES servers(guild_id) ON DELETE CASCADE,
                    last_shuffle TIMESTAMP NOT NULL,
                    triggered_by BIGINT NOT NULL
                )
            ''')

            # Shuffle history table for logging (optional, for future features)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS shuffle_history (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT REFERENCES servers(guild_id) ON DELETE CASCADE,
                    triggered_by BIGINT NOT NULL,
                    users_affected INTEGER NOT NULL,
                    roles_shuffled TEXT[], -- Array of role names
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            print("📋 Database tables created/verified")

    # Server management
    async def add_server(self, guild_id: int, guild_name: str):
        """Add or update a server in the database."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO servers (guild_id, guild_name, updated_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (guild_id) 
                DO UPDATE SET guild_name = $2, updated_at = CURRENT_TIMESTAMP
            ''', guild_id, guild_name)

    async def remove_server(self, guild_id: int):
        """Remove a server and all associated data."""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM servers WHERE guild_id = $1', guild_id)

    # Shuffleable roles management
    async def add_shuffleable_role(self, guild_id: int, role_id: int, role_name: str, added_by: int) -> bool:
        """Add a role to the shuffleable roles list."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO shuffleable_roles (guild_id, role_id, role_name, added_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id, role_id) DO NOTHING
                ''', guild_id, role_id, role_name, added_by)
                return True
        except Exception as e:
            print(f"Error adding shuffleable role: {e}")
            return False

    async def remove_shuffleable_role(self, guild_id: int, role_id: int) -> bool:
        """Remove a role from the shuffleable roles list."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM shuffleable_roles 
                    WHERE guild_id = $1 AND role_id = $2
                ''', guild_id, role_id)
                return result != "DELETE 0"
        except Exception as e:
            print(f"Error removing shuffleable role: {e}")
            return False

    async def get_shuffleable_roles(self, guild_id: int) -> List[dict]:
        """Get all shuffleable roles for a server."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT role_id, role_name, added_by, created_at
                FROM shuffleable_roles
                WHERE guild_id = $1
                ORDER BY role_name
            ''', guild_id)
            
            return [dict(row) for row in rows]

    # Cooldown management
    async def set_shuffle_cooldown(self, guild_id: int, triggered_by: int):
        """Set a cooldown for shuffling in a server."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO shuffle_cooldowns (guild_id, last_shuffle, triggered_by)
                VALUES ($1, CURRENT_TIMESTAMP, $2)
                ON CONFLICT (guild_id)
                DO UPDATE SET last_shuffle = CURRENT_TIMESTAMP, triggered_by = $2
            ''', guild_id, triggered_by)

    async def check_shuffle_cooldown(self, guild_id: int) -> Optional[datetime]:
        """Check if shuffle is on cooldown. Returns None if no cooldown, or datetime when cooldown expires."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT last_shuffle + INTERVAL '5 minutes' as cooldown_expires
                FROM shuffle_cooldowns
                WHERE guild_id = $1
                AND last_shuffle + INTERVAL '5 minutes' > CURRENT_TIMESTAMP
            ''', guild_id)
            
            return row['cooldown_expires'] if row else None

    # Shuffle history
    async def log_shuffle(self, guild_id: int, triggered_by: int, users_affected: int, roles_shuffled: List[str]):
        """Log a shuffle event for history tracking."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO shuffle_history (guild_id, triggered_by, users_affected, roles_shuffled)
                VALUES ($1, $2, $3, $4)
            ''', guild_id, triggered_by, users_affected, roles_shuffled)

    async def get_shuffle_history(self, guild_id: int, limit: int = 10) -> List[dict]:
        """Get recent shuffle history for a server."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT triggered_by, users_affected, roles_shuffled, timestamp
                FROM shuffle_history
                WHERE guild_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            ''', guild_id, limit)
            
            return [dict(row) for row in rows]


# Utility function to load database from config
def load_database_config():
    """Load database configuration from config.json or environment variables."""
    config = {}
    
    # Try loading from environment variables first (for production)
    if os.getenv('DB_HOST'):
        config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
    else:
        # Fall back to config.json (for development)
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)
                config = data['database']
        except FileNotFoundError:
            print("❌ No config.json found and no environment variables set")
            raise
    
    return config