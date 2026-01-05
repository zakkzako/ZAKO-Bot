import subprocess
import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')

async def perform_full_update():
    """GitHubから最新コードをダウンロードするのみ(反映はしない)"""
    try:
        subprocess.run(["git", "fetch"], check=True, capture_output=True)
        status = subprocess.check_output(["git", "status", "-uno"]).decode("utf-8")

        if "Your branch is behind" in status:
            log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
            print(f"[{log_time}] [Updater] 新しい更新が見つかりました。ダウンロード中...")
            subprocess.run(["git", "pull"], check=True)
            print(f"[{log_time}] [Updater] ダウンロード完了。/admin_reload を実行して反映してください。")
            return True
    except Exception as e:
        print(f"[Updater] エラー: {e}")
    return False
