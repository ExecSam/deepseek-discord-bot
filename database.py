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
                    model_channel_id INTEGER
                )
            """)
            await db.commit()

    async def set_api_key(self, guild_id: int, api_key: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (guild_id, api_key) VALUES (?, ?)",
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
            await db.execute(
                "INSERT OR REPLACE INTO settings (guild_id, current_model) VALUES (?, ?)",
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
            await db.execute(
                """INSERT OR REPLACE INTO settings 
                   (guild_id, model_message_id, model_channel_id) 
                   VALUES (?, ?, ?)""",
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