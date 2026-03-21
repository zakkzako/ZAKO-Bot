import discord
import datetime
import jst
import logging
import database  

JST = jst.get_jst()

# 直近の送信時刻を記録する変数
last_sent_hour = None

logger = logging.getLogger(__name__)

async def announce_time(bot):
    """毎正時に実行される時報処理"""
    
    # 現在時刻を取得
    now = datetime.datetime.now(JST)

    # 00分であることを確認（30秒間隔のループで呼ばれる想定）
    if now.minute == 0:
        # 2. 通知済みチェック: 既にこの時刻に送信済みであれば何もしない
        global last_sent_hour
        current_hour_key = (now.year, now.month, now.day, now.hour)
        if last_sent_hour == current_hour_key:
            return

        # 3. データベースから設定を読み込む
        # JSON 操作（os.path.exists や json.load）を削除し、DB への問い合わせに差し替え
        try:
            row = await database.fetch_one(
                "SELECT value FROM system_config WHERE key = ?", 
                ('announcement_channel',)
            )
            
            # 設定が存在しない場合は終了
            if not row or not row['value']:
                return

            # 保存されている ID（文字列）を整数に変換
            channel_id = int(row['value'])
            
        except Exception as e:
            logger.error(f"Database Query Error (jikoku): {e}")
            return
        
        # 4. メッセージ送信処理
        channel = bot.get_channel(channel_id)
        if channel:
            msg = f"{now.hour}時をお知らせします"
            try:
                await channel.send(msg)
                # 送信成功後、この時刻を記録
                last_sent_hour = current_hour_key
                logger.info(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】時報を送信しました: {msg}")
            except discord.DiscordException as e:
                logger.error(f"Discord API Error: {e}")
