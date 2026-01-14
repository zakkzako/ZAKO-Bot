import pytz

def get_jst():
    """
    日本標準時 (JST) のタイムゾーンオブジェクトを取得します。

    Returns:
        pytz.timezone: 日本標準時のタイムゾーンオブジェクト
    """
    return pytz.timezone('Asia/Tokyo')
