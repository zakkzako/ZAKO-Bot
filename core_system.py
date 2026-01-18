import general_commands, admin_commands, economy_commands, gambling_commands
import discord
from discord import app_commands
import datetime
import pytz
import importlib
import os
import json
import work
import updater
import jikoku
import economy
import jst
import logging

JST = jst.get_jst()
def _parse_admin_ids(env_val):
    if not env_val:
        return []
    try:
        parts = [p.strip().strip('"').strip("'") for p in env_val.split(',') if p.strip()]
        return [int(p) for p in parts]
    except Exception:
        return []

admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = _parse_admin_ids(admin_id_env)
logger = logging.getLogger(__name__)

NOTIFICATION_TYPE_WORK = 'work'
NOTIFICATION_TYPE_EXTERNAL_WORK = 'external_work'
WORK_COOLDOWN_MINUTES = 20

async def init_system(bot):
    try: await bot.tree.sync()
    except Exception as e: logger.error(f"Sync Error: {e}", exc_info=True)

# ... 以下は既存実装（省略） ...
