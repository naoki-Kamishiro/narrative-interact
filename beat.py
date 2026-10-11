"""
ビート注入モジュール（strongモード専用）。
プロットのビート待ち行列を管理し、毎ターン1ビートをAPIコピーに注入する。
"""

import re

# timingのソート辞書（表記ゆれ吸収）
TIMING_ORDER = {
    "序盤": 0,
    "中盤": 1,
    "クライマックス直前": 2,
    "クライマックス": 3,
}

# 二次ソート: ビート種別の優先順
TYPE_ORDER = {
    "misconception": 0,
    "failure": 1,
    "choice": 2,
    "twist": 3,
    "character": 4,
}

# 注入文テンプレート（種別ごと）
_TEMPLATES = {
    "misconception": "今回の描写で、現在いる場所で{content}という出来事を起こすこと。ただし内面の変化ではなく外から観察できる出来事として描写すること。",
    "failure":       "今回の描写で、現在いる場所で{content}という状況を発生させること。プレイヤーの行動とは別に世界の側から引き起こすこと。",
    "choice":        "今回の描写で、{content}という局面をプレイヤーが直面する形で描写すること。選択を迫ること。代償は{cost}。",
    "twist":         "今回の描写で、{content}という出来事を世界の側から発生させること。プレイヤーが関係する行動をとらなくても起こすこと。",
    "character":     "{name}が現在地へ現れ、プレイヤーと接触すること。",
}

def build_queue(plot: dict) -> list:
    """プロットからビート待ち行列を生成する。"""
    queue = []

    for item in plot.get("misconceptions", []):
        queue.append({
            "src": "misconceptions",
            "src_idx": plot["misconceptions"].index(item),
            "type": "misconception",
            "timing": item.get("timing", "序盤"),
            "content": item.get("content", ""),
            "done": False,
        })

    for item in plot.get("failures", []):
        queue.append({
            "src": "failures",
            "src_idx": plot["failures"].index(item),
            "type": "failure",
            "timing": item.get("timing", "序盤"),
            "content": item.get("content", ""),
            "done": False,
        })

    for item in plot.get("choices", []):
        queue.append({
            "src": "choices",
            "src_idx": plot["choices"].index(item),
            "type": "choice",
            "timing": item.get("timing", "中盤"),
            "content": item.get("description", ""),
            "cost": item.get("cost", ""),
            "done": False,
        })

    for item in plot.get("twists", []):
        queue.append({
            "src": "twists",
            "src_idx": plot["twists"].index(item),
            "type": "twist",
            "timing": item.get("timing", "中盤"),
            "content": item.get("content", ""),
            "done": False,
        })

    # キャラクター登場ビート（charactersから生成）
    protagonist_name = plot.get("protagonist", {}).get("name", "")
    for c in plot.get("characters", []):
        name = c.get("name", "").strip(": ").strip()
        if name and name != protagonist_name:
            queue.append({
                "src": "characters",
                "src_idx": plot["characters"].index(c),
                "type": "character",
                "timing": "序盤",
                "name": name,
                "done": False,
            })

    # ソート: timing → type
    queue.sort(key=lambda b: (
        TIMING_ORDER.get(b["timing"], 99),
        TYPE_ORDER.get(b["type"], 99),
    ))

    return queue


def make_injection(beat: dict) -> str:
    """ビートから注入文を生成する。"""
    t = beat["type"]
    tmpl = _TEMPLATES.get(t, "")
    if t == "character":
        return tmpl.format(name=beat.get("name", ""))
    elif t == "choice":
        return tmpl.format(content=beat.get("content", ""), cost=beat.get("cost", ""))
    else:
        return tmpl.format(content=beat.get("content", ""))


def get_current_beat(queue: list, ptr: int) -> dict | None:
    """現在のポインタが指すビートを返す。キューが尽きたらNone。"""
    while ptr < len(queue):
        beat = queue[ptr]
        if not beat["done"]:
            return beat
        ptr += 1
    return None


def inject(messages: list, queue: list, ptr: int) -> tuple[list, str | None]:
    """
    API送信用メッセージリストの最後のuserメッセージに注入文を付加する。
    戻り値: (注入後メッセージリスト, 注入したビートのデバッグ情報 or None)
    """
    beat = get_current_beat(queue, ptr)
    if beat is None:
        return messages, None

    injection = make_injection(beat)
    if not injection:
        return messages, None

    # コピーを作って最後のuserメッセージに付加（元のhistoryは変更しない）
    msgs = [dict(m) for m in messages]
    for i in reversed(range(len(msgs))):
        if msgs[i]["role"] == "user":
            msgs[i] = dict(msgs[i])
            msgs[i]["content"] = msgs[i]["content"] + f"\n（GMへの場面指示: {injection}）"
            break

    debug = f"[BEAT] ptr={ptr} type={beat['type']} timing={beat['timing']}"
    return msgs, debug


def detect_character(response: str, name: str) -> bool:
    """GM応答にキャラクター名が含まれるか照合する。"""
    return name in response


def advance(queue: list, ptr: int, response: str) -> tuple[list, int]:
    """
    現在ビートが描写されたか確認し、ポインタを進める。
    characterビートは名前照合で確認。それ以外は1回注入で信頼して進める。
    戻り値: (更新後queue, 新ptr)
    """
    beat = get_current_beat(queue, ptr)
    if beat is None:
        return queue, ptr

    if beat["type"] == "character":
        name = beat.get("name", "")
        if detect_character(response, name):
            queue[ptr]["done"] = True
            return queue, ptr + 1
        else:
            # 未検出: doneのまま保留、次ターンも再注入
            import sys
            print(f"[BEAT] character '{name}' not detected, re-injecting next turn", file=sys.stderr)
            return queue, ptr
    else:
        # 出来事系は1回注入で信頼して進める
        queue[ptr]["done"] = True
        return queue, ptr + 1


def filter_output(response: str) -> str:
    """GM出力から全角括弧のみの段落（GMの判断理由漏れ）を除去する。"""
    lines = response.split("\n")
    filtered = []
    for line in lines:
        stripped = line.strip()
        # （...）だけの行を除去
        if re.fullmatch(r'（[^）]*）', stripped):
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def handle_ending_suppression(queue: list, ptr: int) -> tuple[list, int, bool]:
    """
    【エンディング】が早出しされた場合の処理。
    未登場キャラクタービートのみ残し、それ以外を破棄。
    抑止は1回限り（ending_suppressedフラグはstate側で管理）。
    戻り値: (更新後queue, 新ptr, 抑止したか)
    """
    # 未完了のcharacterビートだけ抽出
    pending_chars = [b for b in queue[ptr:] if b["type"] == "character" and not b["done"]]

    if not pending_chars:
        # 注入するものがない: エンディングを通す
        return queue, ptr, False

    # characterビートだけを残し、残りは破棄（done=Trueにして読み飛ばす）
    for i in range(ptr, len(queue)):
        if queue[i]["type"] != "character":
            queue[i]["done"] = True

    import sys
    print(f"[BEAT] ending suppressed: {len(pending_chars)} character beat(s) remaining", file=sys.stderr)
    return queue, ptr, True
