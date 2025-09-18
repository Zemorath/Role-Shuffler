# 🎲 Discord Role Shuffler Bot

A Discord bot that randomly shuffles users between configured roles, perfect for creating dynamic groups and mixing up team compositions.

## ✨ Features

- **Role Shuffling**: Randomly redistribute users among configured roles
- **Permission Control**: Only users with Manage Roles permission can configure and trigger shuffles
- **Confirmation System**: 5-minute confirmation window with Yes/No buttons
- **Cooldown Protection**: 5-minute cooldown between shuffles to prevent spam
- **Multi-Server Support**: Works across multiple Discord servers
- **Database Persistence**: PostgreSQL backend stores role configurations and shuffle history
- **Smart Role Management**: Only shuffles roles the bot can actually manage

## 🚀 Commands

### `/shuffle`
Randomly shuffle users between configured roles.
- Requires: Manage Roles permission
- Shows confirmation dialog with role distribution preview
- 5-minute timeout for confirmation
- 5-minute cooldown after successful shuffle

### `/config-roles add @role`
Add a role to the shuffleable roles list.
- Requires: Manage Roles permission
- Only roles the bot can manage will work
- Role must be below bot's highest role

### `/config-roles remove @role`
Remove a role from the shuffleable roles list.
- Requires: Manage Roles permission

### `/config-roles list`
Show all configured shuffleable roles and their member counts.
- Requires: Manage Roles permission
- Shows which roles are deleted or empty

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database
- Discord bot token

### 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token (keep it secret!)
5. Under "Privileged Gateway Intents", enable:
   - Server Members Intent
6. Under "Bot Permissions", select:
   - Manage Roles
   - Use Slash Commands

### 2. Invite Bot to Server
1. Go to "OAuth2" > "URL Generator"
2. Select "bot" and "applications.commands" scopes
3. Select "Manage Roles" permission
4. Copy the generated URL and open it to invite the bot

### 3. Setup Database
```sql
-- Create database and user (as postgres user)
CREATE DATABASE role_shuffler;
CREATE USER bot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE role_shuffler TO bot_user;
```

### 4. Install Dependencies
```bash
# Clone the repository
git clone <repository-url>
cd Role-Shuffler

# Install Python dependencies
pip install -r requirements.txt
```

### 5. Configure Bot
Option A - Using config.json (Development):
```json
{
    "bot_token": "your_bot_token_here",
    "database": {
        "host": "localhost",
        "port": 5432,
        "database": "role_shuffler",
        "user": "bot_user",
        "password": "your_secure_password"
    }
}
```

Option B - Using Environment Variables (Production):
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
BOT_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=role_shuffler
DB_USER=bot_user
DB_PASSWORD=your_secure_password
```

### 6. Run the Bot
```bash
python bot.py
```

## 📁 Project Structure
```
Role-Shuffler/
├── bot.py                 # Main bot file
├── database.py           # Database operations
├── commands/
│   ├── __init__.py
│   ├── config.py         # Role configuration commands
│   └── shuffle.py        # Shuffle command logic
├── utils/
│   ├── __init__.py
│   └── permissions.py    # Permission checking utilities
├── requirements.txt      # Python dependencies
├── config.json          # Bot configuration (optional)
├── .env.example         # Environment variables template
└── README.md           # This file
```

## 🔧 How It Works

1. **Setup Phase**: Server admins use `/config-roles add` to specify which roles should be shuffleable
2. **Shuffle Phase**: Users with permissions use `/shuffle` to trigger a redistribution
3. **Confirmation**: Bot shows a preview and waits for confirmation (5 minutes max)
4. **Execution**: All users are removed from their current shuffleable roles and randomly reassigned
5. **Cooldown**: 5-minute cooldown prevents immediate re-shuffling

## 🛡️ Permissions

### User Permissions Required
- **Manage Roles** OR **Administrator** permission in the server
- Must be able to use slash commands

### Bot Permissions Required
- **Manage Roles**: To add/remove roles from users
- **Use Slash Commands**: To register and respond to commands
- **Send Messages**: To send responses and confirmations

### Role Hierarchy
- Bot must have a role higher than the roles it needs to manage
- Bot cannot manage roles that are equal to or higher than its highest role
- @everyone role cannot be shuffled

## 🗃️ Database Schema

The bot uses PostgreSQL with the following tables:
- `servers`: Guild information
- `shuffleable_roles`: Configured roles for each server
- `shuffle_cooldowns`: Cooldown tracking per server
- `shuffle_history`: Log of shuffle events (for future features)

## 🚨 Troubleshooting

### Common Issues

**"I cannot manage the role"**
- Check that bot's role is higher than the target role
- Ensure bot has "Manage Roles" permission
- Target role cannot be @everyone

**"No shuffleable roles configured"**
- Use `/config-roles add @role` to add roles first
- Ensure roles have members in them

**"Shuffle on cooldown"**
- Wait 5 minutes between shuffles
- Cooldown is per-server, not global

**Database connection errors**
- Verify PostgreSQL is running
- Check database credentials in config
- Ensure database and user exist

### Bot Not Responding
1. Check bot is online in Discord
2. Verify bot has slash command permissions
3. Try re-inviting bot with updated permissions
4. Check console for error messages

## 🔮 Future Features

- Shuffle history viewing
- Custom cooldown times per server
- Role weight/priority system
- Scheduled automatic shuffles
- Shuffle templates for different scenarios

## 🤝 Contributing

Feel free to submit issues and pull requests! Make sure to:
1. Test your changes thoroughly
2. Follow the existing code style
3. Update documentation as needed

## 📄 License

This project is open source. Feel free to use and modify as needed.

---

**Need help?** Check the troubleshooting section or create an issue on GitHub!