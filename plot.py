"""
プロット生成モジュール。
プロットはimmutable（不変）扱い。更新は圧縮フェーズのみ。
"""

import json
import re
from json_repair import repair_json
from api import chat_json
from prompt import SYSTEM_PLOT, build_plot_message
from display import system_print

MAX_RETRIES = 3

def generate(genre: str, title: str) -> dict:
    system_print("プロットを生成中...")
    messages = [
        {"role": "system", "content": SYSTEM_PLOT},
        {"role": "user",   "content": build_plot_message(genre, title)},
    ]
    for attempt in range(1, MAX_RETRIES + 1):
        raw = chat_json(messages)
        result = _parse(raw)
        if result:
            system_print("プロット生成完了")
            return result
        if attempt < MAX_RETRIES:
            system_print(f"再試行中... ({attempt}/{MAX_RETRIES})")
    system_print("プロット生成に失敗しました。プロットなしで続行します。")
    return {}

def _parse(raw: str) -> dict:
    if raw.startswith("[ERROR"):
        system_print("プロット生成中にエラーが発生しました")
        return {}

    cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()
    cleaned = re.sub(r"```", "", cleaned).strip()

    # まず通常のJSON解析を試みる
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 解析に失敗した場合、軽微な構文ミス（クォート欠落・末尾カンマ等）の
    # 自動修復を試みる
    try:
        repaired = repair_json(cleaned)
        result = json.loads(repaired)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    system_print("プロットのJSON解析に失敗しました")
    return {}
