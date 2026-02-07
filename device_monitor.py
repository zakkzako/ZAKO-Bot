import discord
import subprocess
import json
import os
import logging
import re
import jst

logger = logging.getLogger(__name__)

async def update_device_status(bot):
    BATTERY_CH_ID = int(os.getenv('BATTERY_CH_ID', 0))
    CPU_CH_ID     = int(os.getenv('CPU_CH_ID', 0))
    RAM_CH_ID     = int(os.getenv('RAM_CH_ID', 0))

    # カッコ付きの時刻文字列を作成
    now = jst.now()
    time_suffix = f"({now.strftime('%H時%M分時点')})"

    try:
        # 1. 電池情報の更新
        try:
            res = subprocess.check_output(["termux-battery-status"], timeout=5).decode("utf-8")
            data = json.loads(res)
            msg = f"電池残量-{data['percentage']}%"
            if data['status'] == "CHARGING": msg += "【充電中】"
            
            full_msg = f"{msg} {time_suffix}"
            ch = bot.get_channel(BATTERY_CH_ID) or await bot.fetch_channel(BATTERY_CH_ID)
            if ch and ch.name != full_msg: await ch.edit(name=full_msg)
        except Exception as e:
            logger.error(f"Battery Error: {e}")

        # 2. CPU使用率の更新 (画像2749.pngの形式に対応)
        try:
            cpu_res = subprocess.check_output("top -n 1 -b", shell=True).decode("utf-8")
            # "0%user" のような形式から数字を抽出
            user_match = re.search(r'(\d+)%user', cpu_res)
            sys_match = re.search(r'(\d+)%sys', cpu_res)
            
            if user_match and sys_match:
                # UserとSystemの合計を計算
                usage = int(user_match.group(1)) + int(sys_match.group(1))
                cpu_text = f"{usage}%"
            else:
                cpu_text = "取得中"
            
            full_msg = f"cpu-{cpu_text} {time_suffix}"
            ch = bot.get_channel(CPU_CH_ID) or await bot.fetch_channel(CPU_CH_ID)
            if ch and ch.name != full_msg: await ch.edit(name=full_msg)
        except Exception as e:
            logger.error(f"CPU Error: {e}")

        # 3. RAM残り容量の更新 (時点を追加)
        try:
            ram_res = subprocess.check_output("free -m | grep Mem", shell=True).decode("utf-8")
            parts = ram_res.split()
            # free -m の available は 7番目 (index 6)
            available_mb = parts[6]
            
            full_msg = f"ram残り-{available_mb}mb {time_suffix}"
            ch = bot.get_channel(RAM_CH_ID) or await bot.fetch_channel(RAM_CH_ID)
            if ch and ch.name != full_msg: await ch.edit(name=full_msg)
        except Exception as e:
            logger.error(f"RAM Error: {e}")

    except Exception as e:
        logger.error(f"Device Monitor Global Error: {e}")
