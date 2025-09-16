# Noema Discord Bot

A powerful Discord bot built with discord.py that creates dynamic community rooms and manages voice/text channel pairs automatically.

## Features

### 🏠 Community Room Management
- **Automatic Room Creation**: When users join designated community channels, the bot automatically creates personal voice and text channels
- **Smart Channel Pairing**: Voice and text channels are paired together and managed as a unit
- **Auto-Cleanup**: Empty rooms are automatically deleted when users leave
- **Role-Based Permissions**: Founder and Co-founder roles have special privileges

### 🎮 Commands

#### Basic Commands
- `/ping` - Check if the bot is responsive
- `/hi` - Basic health check command

#### Community Management
- `/selection_community_channels` - Set a voice channel as a community channel (Founder/Co-founder only)
- `/remove_room` - Remove a room by selecting voice or text channels (Founder/Co-founder only)

#### Administration
- `/reload` - Reload bot commands (Admin only)

### 🔧 Technical Features
- **Modular Architecture**: Commands are organized using Discord.py Cogs for maintainability
- **Comprehensive Logging**: All actions are logged to both console and file
- **Environment Variable Configuration**: Secure token management
- **Slash Commands**: Modern Discord interaction system

## Installation

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- Required Python packages (see requirements.txt)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Noema-Bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## Bot Setup

### Discord Application Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token and add it to your `.env` file
5. Enable the following intents:
   - Message Content Intent
   - Server Members Intent
   - Voice State Intent

### Server Setup
1. Invite the bot to your server with appropriate permissions:
   - Manage Channels
   - Move Members
   - Send Messages
   - View Channels
   - Connect to Voice Channels

2. Create the following roles (if they don't exist):
   - `Founder`
   - `Co-founder` or `cofounder`

## Usage

### Setting Up Community Channels
1. Use `/selection_community_channels` to designate a voice channel as a community channel
2. Only users with Founder or Co-founder roles can set community channels

### How Community Rooms Work
1. When a user joins a designated community channel, the bot automatically:
   - Creates a personal voice channel named after the user
   - Creates a paired text channel with the same name
   - Moves the user to their personal voice channel
   - Sends a welcome message in the text channel

2. When a user leaves their personal room and it becomes empty:
   - The bot automatically deletes both the voice and text channels
   - Channel pairs are cleaned up from memory

### Managing Rooms
- Use `/remove_room` to manually delete rooms by selecting either the voice or text channel
- The bot will automatically delete the paired channel as well
- Only Founders and Co-founders can remove rooms

## Project Structure

```
Noema-Bot/
├── bot.py                          # Main bot file
├── commands/                       # Command modules (Cogs)
│   ├── __init__.py
│   ├── ping.py                     # Basic ping command
│   ├── hi.py                       # Health check command
│   ├── selection_community_channels.py  # Community channel setup
│   ├── remove_room.py              # Room removal command
│   ├── reload.py                   # Command reload utility
│   └── voice_events.py             # Voice state event handling
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (create this)
├── bot.log                        # Bot logs (auto-generated)
└── README.md                      # This file
```

## Configuration

### Environment Variables
- `DISCORD_TOKEN`: Your Discord bot token (required)

### Logging
The bot logs all activities to:
- Console output
- `bot.log` file

Log levels include:
- INFO: Normal operations
- WARNING: Unauthorized access attempts
- ERROR: Failed operations

## Permissions

### Role Requirements
- **Founder/Co-founder**: Can set community channels and remove rooms
- **Administrator**: Can reload bot commands
- **All Users**: Can use basic commands (ping, hi)

### Bot Permissions
The bot requires the following permissions:
- Manage Channels
- Move Members
- Send Messages
- View Channels
- Connect to Voice Channels

## Troubleshooting

### Common Issues

1. **Bot not responding to commands**
   - Check if the bot token is correct in `.env`
   - Ensure the bot has proper permissions
   - Verify slash commands are synced

2. **Cannot create channels**
   - Check bot permissions in the server
   - Ensure the bot has "Manage Channels" permission
   - Verify the category has proper permissions

3. **Commands not loading**
   - Check the console for extension loading errors
   - Ensure all Python files in the commands directory are valid
   - Verify the bot has proper intents enabled

### Logs
Check `bot.log` for detailed error information and debugging.

## License

This project is licensed under the MIT License - see the LICENSE file for details.