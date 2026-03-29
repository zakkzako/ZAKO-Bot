import subprocess
import json
import os
import logging
import re
import asyncio
import math
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

async def update_device_status(bot):
    BATTERY_CH_ID = int(os.getenv('BATTERY_CH_ID', 0))
    CPU_CH_ID     = int(os.getenv('CPU_CH_ID', 0))
    RAM_CH_ID     = int(os.getenv('RAM_CH_ID', 0))

    jst_time = timezone(timedelta(hours=9))
    time_str = datetime.now(jst_time).strftime('%H時%M分')

    # 1. バッテリー (全角％)
    async def get_battery_status():
        process = await asyncio.create_subprocess_exec(
            "termux-battery-status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8")

    try:
        res = await get_battery_status()
        data = json.loads(res)
        pct = data.get("percentage", 0)
        st_jp = {"charging": "充電中", "discharging": "放電中", "full": "満充電"}.get(data.get("status", "").lower(), "待機")
        await _update_ch(bot, BATTERY_CH_ID, f"bat-{st_jp}{pct}％_{time_str}")
    except Exception as e:
        logger.error(f"Battery Error: {e}")

    # 2. CPU (0％回避・全角％)
    async def get_cpu_status():
        process = await asyncio.create_subprocess_shell(
            "top -n 2 -d 3 -b",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8")

    try:
        # 3秒間の平均を取得
        cpu_res = await get_cpu_status()
        parts = cpu_res.split("Tasks:")
        last_top = parts[-1] if len(parts) >= 2 else cpu_res

        idle_match = re.search(r'(\d+)%idle', last_top)
        total_match = re.search(r'(\d+)%cpu', last_top)

        if idle_match and total_match:
            usage = (int(total_match.group(1)) - int(idle_match.group(1))) / (int(total_match.group(1)) / 100)
            # 0％にならないよう切り上げ
            usage_int = math.ceil(usage) if usage > 0 else 0
            if usage > 0 and usage_int == 0: usage_int = 1
            
            await _update_ch(bot, CPU_CH_ID, f"cpu-{usage_int}％_{time_str}")
        else:
            await _update_ch(bot, CPU_CH_ID, f"cpu-active％_{time_str}")
    except Exception as e:
        logger.error(f"CPU Error: {e}")

    # 3. RAM (MB表示から％表示へ変更)
    async def get_ram_status():
        process = await asyncio.create_subprocess_shell(
            "free -m",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8")

    try:
        ram_res = await get_ram_status()
        # free -m の出力を解析
        lines = ram_res.strip().split('\n')
        for line in lines:
            if "Mem:" in line:
                p = line.split()
                total_mem = int(p[1])
                used_mem  = int(p[2])
                # 使用率(％) = (使用量 / 全容量) * 100
                ram_usage = int((used_mem / total_mem) * 100)
                await _update_ch(bot, RAM_CH_ID, f"ram-{ram_usage}％_{time_str}")
                break
    except Exception as e:
        logger.error(f"RAM Error: {e}")

async def _update_ch(bot, ch_id, name):
    if ch_id == 0: return
    try:
        ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
        if ch and ch.name != name:
            await ch.edit(name=name)
            await asyncio.sleep(2.5)
    except Exception as e:
        logger.warning(f"Discord Edit Fail: {e}")
