"""adaptive の逸脱判定（api.check_deviation）が正しく yes/no を返しているかを調べる確認用スクリプト。

本番と同じ問い合わせ文で、明らかに逸脱した行動3つと、筋どおりの行動3つを判定させ、
LLMの生の応答（content・reasoning_content・finish_reason）をそのまま表示する。
推論オフの指定（reasoning_effort）の有無と、max_tokens（本番は4）の大小も切り替えて比べる。

使い方：LM Studio でモデルを1つだけロードし、サーバーを起動してから
    python tools/check_deviation_probe.py
結果を tools/check_deviation_probe_result.json に保存する（そのファイルを貼ってもらえれば判断できる）。
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config import LM_STUDIO_URL, API_KEY  # noqa: E402

URL = LM_STUDIO_URL.rstrip("/") + "/chat/completions"
KEYWORDS = ["鐘の館", "司祭", "鐘を鳴らす儀式", "案内人", "封印された異形"]
CASES = [
    ("明らかな逸脱", ["館を出て麓の町へ向かう。", "町の食堂で働き口を探す。", "パン屋の主人と開店の準備を始める。"]),
    ("筋どおり", ["案内人に鐘の場所を尋ねる。", "司祭の部屋の扉を調べる。", "鐘楼へ続く階段を上る。"]),
]
# (名前, 推論オフ指定を付けるか, max_tokens)
VARIANTS = [
    ("本番どおり（推論オフ・max_tokens=4）", True, 4),
    ("推論オフなし・max_tokens=4", False, 4),
    ("推論オフ・max_tokens=32", True, 32),
]


def build_prompt(actions):
    # api.check_deviation と同じ文面
    actions_text = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(actions))
    return (
        f"以下はテキストRPGのプレイヤーの直近3つの行動です。\n\n"
        f"{actions_text}\n\n"
        f"このゲームの元の物語の中心要素: {'、'.join(KEYWORDS)}\n\n"
        f"これらの行動は、元の物語の中心要素から大きく逸脱し、"
        f"物語が別の方向に進んでいますか？\n"
        f"「yes」か「no」の1単語のみで答えてください。"
    )


def ask(actions, reasoning_off, max_tokens):
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": "あなたはテキストRPGの進行を補助するシステムです。"},
            {"role": "user", "content": build_prompt(actions)},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    if reasoning_off:
        body["reasoning_effort"] = "none"
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": str(e)}
    ch = (data.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    content = msg.get("content") or ""
    return {
        "content": content,
        "reasoning_content": msg.get("reasoning_content") or msg.get("reasoning") or "",
        "finish_reason": ch.get("finish_reason"),
        "判定": "yes" if content.strip().lower().startswith("yes") else "no（yes以外）",
    }


def main():
    results = []
    for vname, ro, mt in VARIANTS:
        for cname, actions in CASES:
            r = ask(actions, ro, mt)
            results.append({"条件": vname, "行動": cname, **r})
            print(f"[{vname}] {cname}: content={r.get('content', '')!r} "
                  f"reasoning={len(r.get('reasoning_content', ''))}字 finish={r.get('finish_reason')} "
                  f"→ {r.get('判定', r.get('error'))}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_deviation_probe_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"保存しました: {out}")


if __name__ == "__main__":
    main()
