import discord
from discord.ext import tasks, commands
import os
from dotenv import load_dotenv
import core_system

load_dotenv()

class TakasumiAuxiliaryBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=discord.Intents.all())

    async def setup_hook(self):
        core_system.register_to_tree(self)
        await core_system.init_system(self)
        self.check_timer_loop.start()

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        # core_system自体のリロードはせず、内部のロジック(check_reminders)を呼び出す
        # work.pyなどの更新は core_system 内の updater が担当します
        await core_system.check_reminders(self)

    async def on_message(self, message):
        await core_system.process_message_event(self, message)
        await self.process_commands(message)

bot = TakasumiAuxiliaryBot()

token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("Error: DISCORD_TOKEN not found in .env file.")
