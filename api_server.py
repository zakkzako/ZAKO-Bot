from flask import Flask, jsonify
import json
import os
import datetime
import pytz
import aiofiles

app = Flask(__name__)

# 設定
REMINDERS_FILE = "reminders.json"
JST = pytz.timezone('Asia/Tokyo')

async def read_file_async(path):
    async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
        return await f.read()

async def write_file_async(path, data):
    async with aiofiles.open(path, mode='w', encoding='utf-8') as f:
        await f.write(data)

async def load_json(path, default):
    if not os.path.exists(path):
        return default
    content = await read_file_async(path)
    try:
        return json.loads(content)
    except:
        return default

@app.route('/check/<int:user_id>', methods=['GET'])
async def check_notification(user_id):
    """
    スマホアプリが30秒〜1分おきに叩くエンドポイント
    """
    queue = load_json(REMINDERS_FILE, [])
    now = datetime.datetime.now(JST)
    
    notifications_to_send = []
    updated = False
    uid_str = user_id # JSON内はintかstrか環境によるため、比較時に調整
    
    for r in queue:
        # ターゲットのユーザーかつ、通知時間を過ぎているかチェック
        if r['user_id'] == user_id:
            target_time = datetime.datetime.fromisoformat(r['target_time'])
            
            # まだアプリ側に通知していないデータがあれば抽出
            if now >= target_time and not r.get("app_done"):
                n_type = r.get('notification_type', 'external_work')
                msg = "ワークの時間が経過しました！" if n_type == 'work' else "外部ワークの時間が経過しました！"
                
                notifications_to_send.append({
                    "id": f"{r['user_id']}_{r['target_time']}", # 簡易的な一意識別子
                    "message": msg,
                    "type": n_type
                })
                
                # アプリに渡したフラグを立てる
                r["app_done"] = True
                updated = True

    # データを渡した場合は、reminders.jsonを更新保存
    if updated:
        await write_file_async(REMINDERS_FILE, json.dumps(queue, ensure_ascii=False, indent=4))

    return jsonify({
        "status": "success",
        "count": len(notifications_to_send),
        "notifications": notifications_to_send
    })

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok", "message": "API Server is running"})

if __name__ == '__main__':
    # 0.0.0.0 は外部（同じWi-Fi内のスマホ等）からの接続を許可する設定です
    # ポートは任意（5000が一般的）
    app.run(host='0.0.0.0', port=5000, debug=False)
