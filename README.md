# DeepSeek Discord Bot

A Discord bot that integrates with DeepSeek's AI models to provide intelligent responses directly in your Discord server.

## Features

- Interact with DeepSeek's AI models directly through Discord
- Support for both DeepSeek Chat and DeepSeek Reasoner models
- Easy model switching with interactive buttons
- Mention the bot to ask questions without commands
- Secure API key management

## Prerequisites

- Python 3.8 or higher
- A Discord Bot Token
- A DeepSeek API Key

## Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
5. Copy your bot token (you'll need this later)
6. Go to "OAuth2" → "URL Generator"
7. Select the following scopes:
   - bot
   - applications.commands
8. Select these bot permissions:
   - Send Messages
   - Read Messages/View Channels
   - Use Slash Commands
   - Embed Links
9. Copy the generated URL and use it to invite the bot to your server

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt