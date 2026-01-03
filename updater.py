import subprocess
import discord
import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')

async def check_for_updates():
    """GitHubの更新を確認し、あればプルする"""
    try:
        # リモート情報を取得
        subprocess.run(["git", "fetch"], check=True, capture_output=True)
        # 現在のブランチが遅れているか確認
        status = subprocess.check_output(["git", "status", "-uno"]).decode("utf-8")
        
        if "Your branch is behind" in status:
            log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
            print(f"[{log_time}] GitHub update detected. Pulling...")
            subprocess.run(["git", "pull"], check=True)
            return True # 更新があった
    except Exception as e:
        print(f"Update Check Error: {e}")
    return False # 更新なし
