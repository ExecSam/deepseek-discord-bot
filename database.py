import aiosqlite
import json

class Database:
    def __init__(self, db_path="bot.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id INTEGER PRIMARY KEY,
                    api_key TEXT,
                    current_model TEXT DEFAULT 'deepseek-chat',
                    model_message_id INTEGER,
                    model_channel_id INTEGER,
                    welcome_sent INTEGER DEFAULT 0
                )
            """)
            await db.commit()

    async def set_api_key(self, guild_id: int, api_key: str):
        async with aiosqlite.connect(self.db_path) as db:
            # Check if record exists
            async with db.execute(
                "SELECT guild_id FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                exists = await cursor.fetchone()
                
            if exists:
                # Update existing record
                await db.execute(
                    "UPDATE settings SET api_key = ? WHERE guild_id = ?",
                    (api_key, guild_id)
                )
            else:
                # Insert new record with defaults
                await db.execute(
                    "INSERT INTO settings (guild_id, api_key, current_model) VALUES (?, ?, 'deepseek-chat')",
                    (guild_id, api_key)
                )
            await db.commit()

    async def get_api_key(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT api_key FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None

    async def set_model(self, guild_id: int, model: str):
        async with aiosqlite.connect(self.db_path) as db:
            # Check if record exists
            async with db.execute(
                "SELECT guild_id FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                exists = await cursor.fetchone()
                
            if exists:
                # Update existing record
                await db.execute(
                    "UPDATE settings SET current_model = ? WHERE guild_id = ?",
                    (model, guild_id)
                )
            else:
                # Insert new record with defaults
                await db.execute(
                    "INSERT INTO settings (guild_id, current_model) VALUES (?, ?)",
                    (guild_id, model)
                )
            await db.commit()

    async def get_model(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT current_model FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 'deepseek-chat'

    async def update_model_message(self, guild_id: int, message_id: int, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            # Check if record exists
            async with db.execute(
                "SELECT guild_id FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                exists = await cursor.fetchone()
                
            if exists:
                # Update existing record
                await db.execute(
                    "UPDATE settings SET model_message_id = ?, model_channel_id = ? WHERE guild_id = ?",
                    (message_id, channel_id, guild_id)
                )
            else:
                # Insert new record with defaults
                await db.execute(
                    """INSERT INTO settings 
                      (guild_id, model_message_id, model_channel_id, current_model) 
                      VALUES (?, ?, ?, 'deepseek-chat')""",
                    (guild_id, message_id, channel_id)
                )
            await db.commit()

    async def get_model_message(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT model_message_id, model_channel_id 
                   FROM settings WHERE guild_id = ?""",
                (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result if result else (None, None)
                
    async def get_welcome_sent(self, guild_id: int):
        """Check if welcome message has been sent to a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT welcome_sent FROM settings WHERE guild_id = ?", 
                (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return bool(result[0]) if result else False
    
    async def set_welcome_sent(self, guild_id: int, sent=True):
        """Mark that welcome message has been sent to a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if record exists
            async with db.execute(
                "SELECT guild_id FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                exists = await cursor.fetchone()
                
            if exists:
                # Update existing record
                await db.execute(
                    "UPDATE settings SET welcome_sent = ? WHERE guild_id = ?",
                    (int(sent), guild_id)
                )
            else:
                # Insert new record with defaults
                await db.execute(
                    "INSERT INTO settings (guild_id, welcome_sent, current_model) VALUES (?, ?, 'deepseek-chat')",
                    (guild_id, int(sent))
                )
            await db.commit()