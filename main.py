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
import views.EconomyApplication as EconomyApplicationViews
import device_monitor

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
        """起動時の初期化"""
        core_system.register_to_tree(self)
        await self.tree.sync()
        # ループを開始
        self.check_timer_loop.start()
        self.reload_core_system_loop.start()
        try:
            await device_monitor.update_device_status(self)
        except Exception as e:
            logger.error(f"Initial Status Update Error: {e}")     
        self.device_status_loop.start() # 1回目完了後に定期実行を開始


    @tasks.loop(minutes=10)
    async def device_status_loop(self):
        """スマホのステータス情報チャンネルを更新"""
        importlib.reload(device_monitor) # 修正を即時反映できるようリロード
        await device_monitor.update_device_status(self)

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        """リマインダーチェック"""
        try:
            # ここに await を追加しました！
            await core_system.check_reminders(self)
        except Exception as e:
            logger.error(f"Loop Error: {e}")


    @tasks.loop(minutes=5)
    async def reload_core_system_loop(self):
        """core_systemのリロード"""
        importlib.reload(core_system)

    async def on_message(self, message):
        """メッセージ受信イベントをcore_systemへ転送"""
        if message.author == self.user:
            return
        try:
            """importlib.reload(core_system)"""
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
        if log_entry.startswith('【20'):
            log_entry = f"```js\n{log_entry}\n```"
        else:
            log_entry = f"```py\n{log_entry}"
            if len(log_entry) > 1900:
                log_entry = log_entry[:1900] + '  ...\n```\n［詳細はコンソールを参照してください］'
            else:
                log_entry += '\n```'
        level = record.levelname
        role_mention = logging_data.get('roles', {}).get(level, '')
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
            print(f"[Webhook Logging Error] Failed to send log via webhook: {e}")

bot = TakasumiAuxiliaryBot()

@bot.event
async def on_ready():
    # 交換申請のビューを追加
    bot.add_view(EconomyApplicationViews.TC_to_EC(bot))
    bot.add_view(EconomyApplicationViews.EC_to_TC(bot))

    # ログイン成功メッセージ
    now = jst.now().strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{now}】{bot.user.name} としてログインしました")

discord_bot_logger = DiscordBotLogger()
logger.addHandler(discord_bot_logger)
logging.getLogger('discord').addHandler(discord_bot_logger)

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

@bot.event
async def on_message_edit(before, after):
    if after.author == bot.user:
        return
    await core_system.process_message_event(bot, after)


# --- 起動 ---
token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    logger.critical("DISCORD_TOKEN is not set in environment variables.")
