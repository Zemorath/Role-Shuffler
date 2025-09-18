import discord
from discord.ext import commands
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

from database import Database, load_database_config
from commands.config import setup as setup_config_commands
from commands.shuffle import setup as setup_shuffle_commands

# Load environment variables from .env file if it exists
load_dotenv()

class RoleShufflerBot(commands.Bot):
    def __init__(self):
        # Define intents - what the bot needs permission to see/do
        intents = discord.Intents.default()
        intents.message_content = True  # Needed to read message content
        intents.guilds = True          # Needed to see guild information
        intents.members = True         # Needed to manage member roles
        
        super().__init__(
            command_prefix='!',  # Not used for slash commands, but required
            intents=intents,
            help_command=None    # Disable default help command
        )
        
        self.database = None

    async def setup_hook(self):
        """This is called when the bot is starting up."""
        print("🤖 Starting Role Shuffler Bot...")
        
        # Initialize database
        try:
            db_config = load_database_config()
            self.database = Database(db_config)
            await self.database.connect()
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            print("Please check your database configuration and ensure PostgreSQL is running.")
            await self.close()
            return

        # Load command modules (cogs)
        try:
            await setup_config_commands(self, self.database)
            await setup_shuffle_commands(self, self.database)
            print("✅ Commands loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load commands: {e}")
            await self.close()
            return

        # Sync slash commands with Discord
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    async def on_ready(self):
        """Called when the bot is ready and connected."""
        print(f"🎉 {self.user} is now online!")
        print(f"📊 Connected to {len(self.guilds)} servers")
        
        # Set bot status
        activity = discord.Game(name="/shuffle | /config-roles")
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        """Called when the bot joins a new server."""
        print(f"📥 Joined new server: {guild.name} (ID: {guild.id})")
        
        # Add server to database
        if self.database:
            await self.database.add_server(guild.id, guild.name)

    async def on_guild_remove(self, guild):
        """Called when the bot is removed from a server."""
        print(f"📤 Left server: {guild.name} (ID: {guild.id})")
        
        # Remove server from database
        if self.database:
            await self.database.remove_server(guild.id)

    async def on_error(self, event, *args, **kwargs):
        """Handle errors that occur during events."""
        print(f"❌ Error in event {event}: {sys.exc_info()}")

    async def close(self):
        """Clean up when the bot is shutting down."""
        print("🔄 Shutting down bot...")
        
        if self.database:
            await self.database.close()
        
        await super().close()
        print("👋 Bot shutdown complete")

def load_bot_token():
    """Load bot token from environment variables or config file."""
    # Try environment variable first (for production/deployment)
    token = os.getenv('BOT_TOKEN')
    
    if not token:
        # Fall back to config.json (for development)
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                token = config.get('bot_token')
        except FileNotFoundError:
            print("❌ No config.json found and BOT_TOKEN environment variable not set")
            return None
    
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Bot token not configured!")
        print("Please set the BOT_TOKEN environment variable or update config.json")
        return None
    
    return token

async def main():
    """Main function to run the bot."""
    # Load bot token
    token = load_bot_token()
    if not token:
        return

    # Create and run bot
    bot = RoleShufflerBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ Invalid bot token provided")
    except discord.PrivilegedIntentsRequired:
        print("❌ Bot requires privileged intents")
        print("Please enable 'Server Members Intent' in the Discord Developer Portal")
    except KeyboardInterrupt:
        print("\n⚠️ Received interrupt signal")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)