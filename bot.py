import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import asyncio
from database import Database
from openai import OpenAI
import os

class DeepseekBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.db = Database()
        
    async def setup_hook(self):
        await self.db.init()
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
        # Sync commands
        await self.tree.sync()
        
        # Send setup message to each guild
        for guild in self.guilds:
            # Try to find a channel named 'general' first
            target_channel = discord.utils.get(guild.text_channels, name='general')
            
            # If no 'general' channel, use the first text channel we can send messages to
            if not target_channel:
                for channel in guild.text_channels:
                    permissions = channel.permissions_for(guild.me)
                    if permissions.send_messages and permissions.embed_links:
                        target_channel = channel
                        break
            
            if target_channel:
                # Check if API key exists for this guild
                api_key = await self.db.get_api_key(guild.id)
                if not api_key:
                    embed = discord.Embed(
                        title="Welcome to DeepSeek Discord Bot! 🎉",
                        description=(
                            "Thank you for adding me to your server!\n\n"
                            "To get started, please run the `/setup` command to configure:\n"
                            "• Your DeepSeek API Key\n"
                            "• Preferred AI Model\n\n"
                            "Once setup is complete, you can use:\n"
                            "• `/ask` - Ask questions\n"
                            "• `/model` - Switch AI models\n"
                            "• Or just mention me in any message!"
                        ),
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="Made with ❤️ by rifts")
                    
                    try:
                        await target_channel.send(embed=embed)
                    except discord.Forbidden:
                        print(f"Cannot send messages in {target_channel.name} in {guild.name}")
                    except Exception as e:
                        print(f"Error sending welcome message to {guild.name}: {str(e)}")

class APIKeyModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Set DeepSeek API Key")
        self.bot = bot
        self.api_key = TextInput(
            label="API Key",
            placeholder="Enter your DeepSeek API key here...",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.api_key)

    async def on_submit(self, interaction: discord.Interaction):
        await self.bot.db.set_api_key(interaction.guild_id, self.api_key.value)
        
        # Test the API key
        client = OpenAI(
            api_key=self.api_key.value,
            base_url="https://api.deepseek.com"
        )
        
        try:
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": "This is a test message from a Discord Bot. If you see this, reply with: API Key Setup Successful. This message is from the DeepSeek API."},
                    ],
                    stream=False
                )
            )
            
            test_message = await interaction.channel.send(response.choices[0].message.content)
            await asyncio.sleep(60)
            await test_message.delete()
            
            await interaction.response.send_message("API key has been set successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error testing API key: {str(e)}", ephemeral=True)

class ModelSelect(View):
    def __init__(self, bot, current_model):
        super().__init__(timeout=None)
        self.bot = bot
        
        chat_button = Button(
            label=f"{'[SELECTED] ' if current_model == 'deepseek-chat' else ''}DeepSeek Chat (Normal)",
            style=discord.ButtonStyle.green if current_model == 'deepseek-chat' else discord.ButtonStyle.grey,
            custom_id="deepseek-chat"
        )
        
        reason_button = Button(
            label=f"{'[SELECTED] ' if current_model == 'deepseek-r1' else ''}DeepSeek R1 (Reasoning)",
            style=discord.ButtonStyle.green if current_model == 'deepseek-r1' else discord.ButtonStyle.grey,
            custom_id="deepseek-r1"
        )
        
        chat_button.callback = self.button_callback
        reason_button.callback = self.button_callback
        
        self.add_item(chat_button)
        self.add_item(reason_button)

    async def button_callback(self, interaction: discord.Interaction):
        model = interaction.data["custom_id"]
        await self.bot.db.set_model(interaction.guild_id, model)
        await interaction.response.send_message(f"Model changed to {model}", ephemeral=True)
        
        # Update the embed
        embed = discord.Embed(
            title="DeepSeek Model Selection",
            description="Select which model you'd like to use:",
            color=discord.Color.blue()
        )
        
        await interaction.message.edit(
            embed=embed,
            view=ModelSelect(self.bot, model)
        )

def create_bot():
    return DeepseekBot()

if __name__ == "__main__":
    bot = create_bot()
    
    @bot.tree.command(name="setup", description="Initial setup for the DeepSeek bot")
    async def setup(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Welcome to DeepSeek Discord Bot!",
            description="Thank you for trying out the project! Made with ❤️ by rifts\n\n"
                       "Available commands:\n"
                       "• /ask - Ask DeepSeek a question\n"
                       "• /model - Select which DeepSeek model to use\n"
                       "• /apikey - Change your API key\n\n"
                       "To get started, click 'Set API Key' below and enter your DeepSeek API key.",
            color=discord.Color.blue()
        )
        
        class SetupView(View):
            def __init__(self, bot):
                super().__init__()
                self.bot = bot

            @discord.ui.button(label="Set API Key", style=discord.ButtonStyle.primary)
            async def set_key(self, interaction: discord.Interaction, button: Button):
                await interaction.response.send_modal(APIKeyModal(self.bot))

            @discord.ui.button(label="Select Model", style=discord.ButtonStyle.secondary)
            async def select_model(self, interaction: discord.Interaction, button: Button):
                api_key = await bot.db.get_api_key(interaction.guild_id)
                if not api_key:
                    await interaction.response.send_message("Please set an API key first!", ephemeral=True)
                    return
                await model(interaction)

        await interaction.response.send_message(embed=embed, view=SetupView(bot))

    @bot.tree.command(name="model", description="Select which DeepSeek model to use")
    async def model(interaction: discord.Interaction):
        api_key = await bot.db.get_api_key(interaction.guild_id)
        if not api_key:
            await interaction.response.send_message("Please run /setup first!", ephemeral=True)
            return

        # Delete previous model message if it exists
        message_id, channel_id = await bot.db.get_model_message(interaction.guild_id)
        if message_id and channel_id:
            try:
                channel = bot.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
                await message.delete()
            except:
                pass

        current_model = await bot.db.get_model(interaction.guild_id)
        embed = discord.Embed(
            title="DeepSeek Model Selection",
            description="Select which model you'd like to use:",
            color=discord.Color.blue()
        )
        
        message = await interaction.response.send_message(
            embed=embed,
            view=ModelSelect(bot, current_model)
        )
        
        # Store the new message details
        message = await interaction.original_response()
        await bot.db.update_model_message(interaction.guild_id, message.id, interaction.channel_id)

    @bot.tree.command(name="ask", description="Ask DeepSeek a question")
    async def ask(interaction: discord.Interaction, message: str):
        api_key = await bot.db.get_api_key(interaction.guild_id)
        if not api_key:
            await interaction.response.send_message("Please run /setup first!", ephemeral=True)
            return

        await interaction.response.defer()

        model = await bot.db.get_model(interaction.guild_id)
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        try:
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": message},
                    ],
                    stream=False
                )
            )
            
            await interaction.followup.send(response.choices[0].message.content)
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")

    @bot.tree.command(name="apikey", description="Change your DeepSeek API key")
    async def apikey(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Change API Key",
            description="Would you like to set a new API key?",
            color=discord.Color.blue()
        )
        
        class APIKeyView(View):
            def __init__(self, bot):
                super().__init__()
                self.bot = bot

            @discord.ui.button(label="Set API Key", style=discord.ButtonStyle.primary)
            async def set_key(self, interaction: discord.Interaction, button: Button):
                await interaction.response.send_modal(APIKeyModal(self.bot))

        await interaction.response.send_message(embed=embed, view=APIKeyView(bot), ephemeral=True)

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        if bot.user in message.mentions and not any(mention.everyone or mention.role for mention in message.mentions):
            api_key = await bot.db.get_api_key(message.guild.id)
            if not api_key:
                await message.reply("Please run /setup first!")
                return

            model = await bot.db.get_model(message.guild.id)
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

            # Remove the bot mention from the message
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()

            try:
                response = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant"},
                            {"role": "user", "content": content},
                        ],
                        stream=False
                    )
                )
                
                await message.reply(response.choices[0].message.content)
            except Exception as e:
                await message.reply(f"Error: {str(e)}")
    # Load token from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found in .env file. Please add DISCORD_TOKEN=your_token_here to your .env file.")
        
    bot.run(token)