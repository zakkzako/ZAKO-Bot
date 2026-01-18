import datetime
import logging

logger = logging.getLogger(__name__)
JST = None
# JST はモジュール外で設定されている想定（既存の jst.get_jst() を使用）

def _extract_user_from_message(message):
    """
    明示的で分かりやすいユーザー特定ロジック
    """
    # 1) message.interaction_metadata が使える場合
    try:
        if getattr(message, "interaction_metadata", None) and getattr(message.interaction_metadata, "user", None):
            return message.interaction_metadata.user
    except Exception:
        logger.debug("interaction_metadata access error", exc_info=True)

    # 2) 直接��ンションがある場合
    try:
        if getattr(message, "mentions", None):
            if len(message.mentions) > 0:
                return message.mentions[0]
    except Exception:
        logger.debug("mentions access error", exc_info=True)

    return None

# 以降の処理は既存の handle_work_detection 等に組み込む想定
