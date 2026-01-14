import discord
from discord.ext import tasks, commands
import importlib
import os
import datetime
import pytz
from dotenv import load_dotenv
import core_system
import jst
import logging

load_dotenv()
JST = jst.get_jst()

# ログ設定
logging.basicConfig(
    level=logging.INFO,  # ログレベルを INFO に設定
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        """logging.FileHandler('bot.log', encoding='utf-8'),  # ファイルにログを記録""" # 検討中🤔 - ファイルサイズが大きくなりそうなんよね | Yamatomato
        logging.StreamHandler()  # コンソールに出力
    ]
)
logger = logging.getLogger(__name__)

class TakasumiAuxiliaryBot(commands.Bot):
    def __init__(self):
        """リアクション検知を含む全てのインテントを有効化"""
        super().__init__(command_prefix='/', intents=discord.Intents.all())

    async def setup_hook(self):
        """起動時の初期化とコマンド同期をcore_systemに委譲"""
        core_system.register_to_tree(self)
        await core_system.init_system(self)
        self.check_timer_loop.start()

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        """リマインダーチェック"""
        try:
            await core_system.check_reminders(self)
        except Exception as e:
            logger.error(f"Loop Error: {e}")

    @tasks.loop(minutes=5)
    def reload_core_system_loop(self):
        """core_systemのリロード"""
        importlib.reload(core_system)

    async def on_message(self, message):
        """メッセージ受信イベントをcore_systemへ転送"""
        if message.author == self.user:
            return
        try:
            importlib.reload(core_system)
            await core_system.process_message_event(self, message)
            await self.process_commands(message)
        except Exception as e:
            logger.error(f"Message Processing Error: {e}")

    # --- 経済システム（換金・購入承認）用の追加 ---
    async def on_raw_reaction_add(self, payload):
        """リアクション追加イベントをcore_systemへ転送"""
        importlib.reload(core_system)
        await core_system.handle_reaction_event(self, payload)

bot = TakasumiAuxiliaryBot()

@bot.event
async def on_ready():
    now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{now}】{bot.user.name} としてログインしました")

token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
