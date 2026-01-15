import pytz

def get_jst():
    """
    日本標準時 (JST) のタイムゾーンオブジェクトを取得します。

    Returns:
        pytz.timezone: 日本標準時のタイムゾーンオブジェクト
    """
    return pytz.timezone('Asia/Tokyo')

def now():
    """
    現在の日本標準時 (JST) の日時を取得します。

    Returns:
        datetime: 現在のJST日時
    """
    jst = get_jst()
    return pytz.utc.localize(pytz.datetime.datetime.utcnow()).astimezone(jst)
