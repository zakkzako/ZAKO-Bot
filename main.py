import discord
from discord.ext import tasks, commands
import importlib
import os
import datetime
import pytz
from dotenv import load_dotenv
import core_system

load_dotenv()
JST = pytz.timezone('Asia/Tokyo')

class TakasumiAuxiliaryBot(commands.Bot):
    def __init__(self):
        # リアクション検知を含む全てのインテントを有効化
        super().__init__(command_prefix='/', intents=discord.Intents.all())

    async def setup_hook(self):
        # 起動時の初期化とコマンド同期をcore_systemに委譲
        core_system.register_to_tree(self)
        await core_system.init_system(self)
        self.check_timer_loop.start()

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        """監視ループ（自動更新を含む）"""
        try:
            importlib.reload(core_system)
            await core_system.check_reminders(self)
        except Exception as e:
            print(f"Loop Error: {e}")

    async def on_message(self, message):
        """メッセージ受信イベントをcore_systemへ転送"""
        if message.author == self.user:
            return
        importlib.reload(core_system)
        await core_system.process_message_event(self, message)
        await self.process_commands(message)

    # --- 経済システム（換金・購入承認）用の追加 ---
    async def on_raw_reaction_add(self, payload):
        """リアクション追加イベントをcore_systemへ転送"""
        importlib.reload(core_system)
        await core_system.handle_reaction_event(self, payload)

bot = TakasumiAuxiliaryBot()

@bot.event
async def on_ready():
    now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
    print(f"【{now}】{bot.user.name}としてログインしました")

token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)

