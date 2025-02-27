import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import asyncio
from database import Database
from openai import OpenAI
import os
from dotenv import load_dotenv

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
        
        # Get guild ID from env
        guild_id = os.getenv('GUILD_ID')
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            # Sync commands to the specific guild
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced commands to guild ID: {guild_id}")
        else:
            print("No GUILD_ID found in .env, commands may take up to an hour to register globally")
            await self.tree.sync()
        
        # Send setup message to each guild - ONLY FOR NEW GUILDS
        for guild in self.guilds:
            # Check if welcome message has been sent already
            welcome_sent = await self.db.get_welcome_sent(guild.id)
            if welcome_sent:
                continue
                
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
                        await self.db.set_welcome_sent(guild.id, True)
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
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Test the API key first before saving
            client = OpenAI(
                api_key=self.api_key.value,
                base_url="https://api.deepseek.com"
            )
            
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": "You are a discord bot that will answer questions."},
                    ],
                    stream=False
                )
            )
            
            # Only save API key if test was successful
            await self.bot.db.set_api_key(interaction.guild_id, self.api_key.value)
            
            # Set default model if not already set
            current_model = await self.bot.db.get_model(interaction.guild_id)
            if not current_model:
                await self.bot.db.set_model(interaction.guild_id, "deepseek-chat")
                
            await interaction.followup.send("API key has been set successfully! You can now use /ask or mention me to chat.", ephemeral=True)
            
            # Update the setup view if this was from setup
            try:
                await interaction.message.edit(view=SetupView(self.bot, True))
            except:
                pass
                
        except Exception as e:
            await interaction.followup.send(f"Error testing API key: {str(e)}", ephemeral=True)

class SetupView(View):
    def __init__(self, bot, api_key_set=False):
        super().__init__(timeout=None)  # Set timeout to None to keep buttons active
        self.bot = bot
        self.api_key_set = api_key_set
        self.update_buttons()

    @discord.ui.button(label="Set API Key", style=discord.ButtonStyle.primary)
    async def set_key(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(APIKeyModal(self.bot))

    @discord.ui.button(label="Select Model", style=discord.ButtonStyle.secondary)
    async def select_model(self, interaction: discord.Interaction, button: Button):
        api_key = await self.bot.db.get_api_key(interaction.guild_id)
        if not api_key:
            await interaction.response.send_message("Please set an API key first!", ephemeral=True)
            return
        
        # Get the command and execute it
        try:
            command = self.bot.tree.get_command("model")
            await interaction.response.defer(ephemeral=True)
            await command.callback(interaction)
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
    
    def update_buttons(self):
        self.select_model.disabled = not self.api_key_set
        return self

class ModelSelect(View):
    def __init__(self, bot, current_model):
        super().__init__(timeout=None)  # Set timeout to None to keep buttons active
        self.bot = bot
        
        # Default to deepseek-chat if current_model is None
        if not current_model:
            current_model = "deepseek-chat"
        
        chat_button = Button(
            label=f"{'[SELECTED] ' if current_model == 'deepseek-chat' else ''}DeepSeek Chat (Normal)",
            style=discord.ButtonStyle.green if current_model == 'deepseek-chat' else discord.ButtonStyle.grey,
            custom_id="deepseek-chat"
        )
        
        reason_button = Button(
            label=f"{'[SELECTED] ' if current_model == 'deepseek-reasoner' else ''}DeepSeek R1 (Reasoning)",
            style=discord.ButtonStyle.green if current_model == 'deepseek-reasoner' else discord.ButtonStyle.grey,
            custom_id="deepseek-reasoner"
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
    bot = DeepseekBot()
    
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
        
        api_key = await bot.db.get_api_key(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=SetupView(bot, api_key is not None))

    @bot.tree.command(name="model", description="Select which DeepSeek model to use")
    async def model(interaction: discord.Interaction):
        api_key = await bot.db.get_api_key(interaction.guild_id)
        if not api_key:
            embed = discord.Embed(
                title="Setup Required",
                description="Please run /setup first and set your API key!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Delete previous model message if it exists
        try:
            message_id, channel_id = await bot.db.get_model_message(interaction.guild_id)
            if message_id and channel_id:
                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.delete()
                    except discord.NotFound:
                        # Message already deleted, continue
                        pass
                    except Exception as e:
                        print(f"Error deleting previous model message: {str(e)}")
        except Exception as e:
            print(f"Error handling previous model message: {str(e)}")

        current_model = await bot.db.get_model(interaction.guild_id)
        embed = discord.Embed(
            title="DeepSeek Model Selection",
            description="Select which model you'd like to use:",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=ModelSelect(bot, current_model)
        )
        
        # Store the new message details
        try:
            message = await interaction.original_response()
            await bot.db.update_model_message(interaction.guild_id, message.id, interaction.channel_id)
        except Exception as e:
            print(f"Error updating model message: {str(e)}")

    @bot.tree.command(name="ask", description="Ask DeepSeek a question")
    async def ask(interaction: discord.Interaction, message: str):
        api_key = await bot.db.get_api_key(interaction.guild_id)
        if not api_key:
            embed = discord.Embed(
                title="Setup Required",
                description="Please run /setup first and set your API key!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        model = await bot.db.get_model(interaction.guild_id)
        if not model:
            # Set default model if not set
            model = "deepseek-chat"
            await bot.db.set_model(interaction.guild_id, model)
            
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
            
            # Split long responses if needed
            content = response.choices[0].message.content
            if len(content) > 2000:
                chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await interaction.followup.send(chunk)
                    else:
                        await interaction.followup.send(f"(continued) {chunk}")
            else:
                await interaction.followup.send(content)
                
        except Exception as e:
            error_message = str(e)
            user_friendly_error = "There was an error communicating with DeepSeek API. "
            
            if "Unauthorized" in error_message or "unauthorized" in error_message.lower():
                user_friendly_error += "Your API key may be invalid. Please set a new key with /apikey."
            elif "not found" in error_message.lower() or "404" in error_message:
                user_friendly_error += f"The model '{model}' may not be available. Try changing models with /model."
            else:
                user_friendly_error += f"Error details: {error_message}"
                
            await interaction.followup.send(user_friendly_error)

    @bot.tree.command(name="apikey", description="Change your DeepSeek API key")
    async def apikey(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Change API Key",
            description="Would you like to set a new API key?",
            color=discord.Color.blue()
        )
        
        api_key = await bot.db.get_api_key(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=SetupView(bot, api_key is not None), ephemeral=True)

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        # Improved mention check logic
        is_mentioned = False
        if bot.user.id in [mention.id for mention in message.mentions]:
            # Make sure it's not a reply to someone else that happens to mention the bot
            if not message.reference or not message.reference.resolved or bot.user.id in [mention.id for mention in message.reference.resolved.mentions]:
                is_mentioned = True
        
        if is_mentioned:
            # Get API key and check if setup is complete
            api_key = await bot.db.get_api_key(message.guild.id)
            if not api_key:
                # More helpful error message with button to run setup
                embed = discord.Embed(
                    title="Setup Required",
                    description="Please set up your DeepSeek API key to use this bot.",
                    color=discord.Color.orange()
                )
                
                class SetupButtonView(View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        
                    @discord.ui.button(label="Run Setup", style=discord.ButtonStyle.primary)
                    async def setup_button(self, interaction: discord.Interaction, button: Button):
                        if interaction.user.id != message.author.id:
                            await interaction.response.send_message("Only the original user can use this button.", ephemeral=True)
                            return
                            
                        command = bot.tree.get_command("setup")
                        await interaction.response.defer(ephemeral=True)
                        await command.callback(interaction)
                
                await message.reply(embed=embed, view=SetupButtonView())
                return

            # Get model, defaulting to deepseek-chat if not set
            model = await bot.db.get_model(message.guild.id)
            if not model:
                model = "deepseek-chat"
                await bot.db.set_model(message.guild.id, model)

            # Remove the bot mention from the message
            content = message.content
            for mention in message.mentions:
                if mention.id == bot.user.id:
                    content = content.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
            
            content = content.strip()
            
            # Don't process empty messages after removing mentions
            if not content:
                await message.reply("How can I help you today?")
                return

            # Show typing indicator
            async with message.channel.typing():
                try:
                    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
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
                    
                    # Handle long responses
                    reply_content = response.choices[0].message.content
                    if len(reply_content) > 2000:
                        chunks = [reply_content[i:i+1900] for i in range(0, len(reply_content), 1900)]
                        first_message = await message.reply(chunks[0])
                        for chunk in chunks[1:]:
                            await message.channel.send(f"(continued) {chunk}", reference=first_message)
                    else:
                        await message.reply(reply_content)
                        
                except Exception as e:
                    error_message = str(e)
                    user_friendly_error = "There was an error communicating with DeepSeek API. "
                    
                    if "Unauthorized" in error_message or "unauthorized" in error_message.lower():
                        user_friendly_error += "Your API key may be invalid. Please set a new key with /apikey."
                    elif "not found" in error_message.lower() or "404" in error_message:
                        user_friendly_error += f"The model '{model}' may not be available. Try changing models with /model."
                    else:
                        user_friendly_error += f"Error details: {error_message}"
                        
                    await message.reply(user_friendly_error)
    
    return bot

if __name__ == "__main__":
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found in .env file. Please add DISCORD_TOKEN=your_token_here to your .env file.")
    
    bot = create_bot()
    bot.run(token)