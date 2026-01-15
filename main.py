import discord
from discord import SyncWebhook
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
        # logging.FileHandler('bot.log', encoding='utf-8'),  # ファイルにログを記録    検討中🤔 - ファイルサイズが大きくなりそうなんよね | Yamatomato
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
        self.reload_core_system_loop.start()
        await self.tree.sync()

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        """リマインダーチェック"""
        try:
            core_system.check_reminders(self)
        except Exception as e:
            logger.error(f"Loop Error: {e}")

    @tasks.loop(minutes=5)
    async def reload_core_system_loop(self):
        """core_systemのリロード"""
        await importlib.reload(core_system)

    async def on_message(self, message):
        """メッセージ受信イベントをcore_systemへ転送"""
        if message.author == self.user:
            return
        try:
            importlib.reload(core_system)
            await self.process_commands(message)
            await core_system.process_message_event(self, message)
        except Exception as e:
            logger.error(f"Message Processing Error: {e}")

    # --- 経済システム（換金・購入承認）用の追加 ---
    async def on_raw_reaction_add(self, payload):
        """リアクション追加イベントをcore_systemへ転送"""
        importlib.reload(core_system)
        await core_system.handle_reaction_event(self, payload)

logging_data = {
    'roles': {
        'DEBUG'   :  '<@&1461192008214249696>',
        'INFO'    :  '<@&1461178511367602189>',
        'WARNING' :  '<@&1461192066326597727>',
        'ERROR'   :  '<@&1461178572164038810>',
        'CRITICAL':  '<@&1461192196735766651>',
    },
    'webhooks': {
        'ALL'     :  os.getenv('DISCORD_LOG_WEBHOOK_URL_ALL'),
        'DEBUG'   :  os.getenv('DISCORD_LOG_WEBHOOK_URL_DEBUG'),
        'INFO'    :  os.getenv('DISCORD_LOG_WEBHOOK_URL_INFO'),
        'WARNING' :  os.getenv('DISCORD_LOG_WEBHOOK_URL_WARNING'),
        'ERROR'   :  os.getenv('DISCORD_LOG_WEBHOOK_URL_ERROR'),
        'CRITICAL':  os.getenv('DISCORD_LOG_WEBHOOK_URL_CRITICAL'),
    }
}

class DiscordBotLogger(logging.Handler):
    def __init__(self):
        super().__init__()
        self.webhook = {
            'ALL'     :  SyncWebhook.from_url(logging_data['webhooks']['ALL']),
            'DEBUG'   :  SyncWebhook.from_url(logging_data['webhooks']['DEBUG']),
            'INFO'    :  SyncWebhook.from_url(logging_data['webhooks']['INFO']),
            'WARNING' :  SyncWebhook.from_url(logging_data['webhooks']['WARNING']),
            'ERROR'   :  SyncWebhook.from_url(logging_data['webhooks']['ERROR']),
            'CRITICAL':  SyncWebhook.from_url(logging_data['webhooks']['CRITICAL']),
        }

    def emit(self, record):
        log_entry = self.format(record)
        if len(log_entry) > 1900:
            log_entry = log_entry[:1900] + '  ...\n［詳細はコンソールを参照してください］'
        level = record.levelname
        role_mention = logging_data.roles.get(level, '')
        message = f"{role_mention}\n{log_entry}" if role_mention else log_entry
        
        """Webhook にログを送信"""
        try:
            message = message.encode('utf-8').decode('utf-8')
            # All に送信
            self.webhook['ALL'].send(message)
            # レベル別に送信
            if level in self.webhook:
                self.webhook[level].send(message)
        except Exception as e:
            logger.error(f"Failed to send log via webhook: {e}")

bot = TakasumiAuxiliaryBot()

@bot.event
async def on_ready():
    now = jst.now().strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{now}】{bot.user.name} としてログインしました")

discord_bot_logger = DiscordBotLogger()
logger.addHandler(discord_bot_logger)
logging.getLogger('discord').addHandler(discord_bot_logger)
logging.getLogger('discord.ext.commands').addHandler(discord_bot_logger)
logging.getLogger('discord.http').addHandler(discord_bot_logger)
logging.getLogger('discord.gateway').addHandler(discord_bot_logger)

@bot.event
async def on_error(event_method, *args, **kwargs):
    """一般的なエラー処理"""
    logger.error(f"Error in {event_method}", exc_info=True)

@bot.event
async def on_command_error(ctx, error):
    """コマンドエラー処理"""
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error(f"Command Error: {error}")

# --- 起動 ---
token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    logger.critical("DISCORD_TOKEN is not set in environment variables.")
