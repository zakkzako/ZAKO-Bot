import discord
from discord.ext import tasks, commands
import importlib
import os
from dotenv import load_dotenv
import core_system

# .envファイルを読み込み
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
        importlib.reload(core_system)
        await core_system.check_reminders(self)

    async def on_message(self, message):
        await core_system.process_message_event(self, message)
        await self.process_commands(message)

bot = TakasumiAuxiliaryBot()

# 環境変数からトークンを取得して起動
token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("Error: DISCORD_TOKEN not found in .env file.")
