import subprocess
import importlib
import sys
import datetime
import pytz

# 日本標準時 (JST) の設定
JST = pytz.timezone('Asia/Tokyo')

async def perform_full_update(target_modules):
    """
    GitHubを確認し、更新があればプルして対象モジュールをリロードする。
    core_system.py から呼び出される。
    """
    try:
        # 1. GitHubのリモート情報を取得
        # capture_output=True でターミナルにログを出さずに処理
        subprocess.run(["git", "fetch"], check=True, capture_output=True)
        
        # 2. 現在のブランチがリモートより遅れているか確認
        status = subprocess.check_output(["git", "status", "-uno"]).decode("utf-8")
        
        if "Your branch is behind" in status:
            log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
            print(f"[{log_time}] [Updater] GitHubに更新を検知。プルを開始します...")
            
            # 3. 最新コードをプル
            subprocess.run(["git", "pull"], check=True)
            
            # 4. 指定されたモジュール（workやupdater自身）をリロード
            for module_name in target_modules:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
            
            print(f"[{log_time}] [Updater] 全モジュールのリロードが完了しました。")
            return True # 更新成功
            
    except subprocess.CalledProcessError as e:
        print(f"[Updater] Git操作中にエラーが発生しました: {e}")
    except Exception as e:
        print(f"[Updater] 予期せぬエラーが発生しました: {e}")
        
    return False # 更新なし、または失敗
