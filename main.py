import discord
from discord.ext import tasks, commands
import importlib
import os
from dotenv import load_dotenv
import core_system

load_dotenv()

class TakasumiAuxiliaryBot(commands.Bot):
    def __init__(self):
        # 全てのIntentを有効化（work検知に必要）
        super().__init__(command_prefix='/', intents=discord.Intents.all())

    async def setup_hook(self):
        # 初回登録
        core_system.register_to_tree(self)
        await core_system.init_system(self)
        self.check_timer_loop.start()

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        """30秒ごとにcore_systemをリロードして監視を実行"""
        try:
            importlib.reload(core_system)
            await core_system.check_reminders(self)
        except Exception as e:
            print(f"[Main Loop Error] {e}")

    async def on_message(self, message):
        """メッセージ受信時も常に最新のロジックで判定"""
        if message.author == self.user:
            return
        
        try:
            importlib.reload(core_system)
            await core_system.process_message_event(self, message)
            await self.process_commands(message)
        except Exception as e:
            print(f"[Main Message Error] {e}")

bot = TakasumiAuxiliaryBot()

token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("Error: DISCORD_TOKEN not found in .env file.")
    
