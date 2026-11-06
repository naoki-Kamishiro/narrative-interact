"""QAT版など推論（シンキング）するモデルで、OpenAI互換API（/v1/chat/completions）のまま
推論をオフにできる指定があるかを調べる確認用スクリプト。

使い方：LM Studio でモデルを1つだけロードし、サーバーを起動してから
    python tools/check_reasoning_off.py
結果の表と、全文を tools/check_reasoning_off_result.json に保存する（そのファイルを貼ってもらえれば判断できる）。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config import LM_STUDIO_URL, API_KEY  # noqa: E402

URL = LM_STUDIO_URL.rstrip("/") + "/chat/completions"

# 役割つきの複数ターン（本番と同じ形）
MESSAGES = [
    {"role": "system", "content": "あなたはTRPGのGMです。日本語で、2〜3文で状況を描写してください。"},
    {"role": "user", "content": "古い屋敷の扉を開ける。"},
    {"role": "assistant", "content": "扉が軋んで開く。埃の匂いが鼻を突く。廊下の奥で燭台が一つだけ灯っている。"},
    {"role": "user", "content": "燭台に近づく。"},
]

# 試す指定（名前, リクエストに足すもの）
VARIANTS = [
    ("基準（指定なし）", {}),
    ("reasoning_effort=none", {"reasoning_effort": "none"}),
    ("reasoning_effort=low", {"reasoning_effort": "low"}),
    ("reasoning={effort:none}", {"reasoning": {"effort": "none"}}),
    ("reasoning=off", {"reasoning": "off"}),
    ("chat_template_kwargs.enable_thinking=false", {"chat_template_kwargs": {"enable_thinking": False}}),
    ("enable_thinking=false", {"enable_thinking": False}),
]

THINK_MARKERS = ("<think>", "</think>", "<|channel|>", "<|think|>", "<thought>", "thought\n")


def call(extra: dict) -> dict:
    body = {"model": "local", "messages": MESSAGES, "max_tokens": 1024, "temperature": 0.7}
    body.update(extra)
    req = urllib.request.Request(
        URL, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}", "sec": round(time.time() - t0, 1)}
    except Exception as e:  # 接続エラーなど
        return {"error": repr(e), "sec": round(time.time() - t0, 1)}
    sec = round(time.time() - t0, 1)
    msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    usage = data.get("usage", {}) or {}
    details = usage.get("completion_tokens_details", {}) or {}
    return {
        "sec": sec,
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
        "reasoning_len": len(reasoning),
        "think_marker_in_content": any(m in content for m in THINK_MARKERS),
        "content": content,
        "reasoning": reasoning[:2000],
        "raw_message_keys": sorted(msg.keys()),
    }


def main():
    print(f"送信先: {URL}\n")
    results = []
    for name, extra in VARIANTS:
        print(f"… {name}", flush=True)
        r = call(extra)
        r["variant"] = name
        results.append(r)
    print("\n指定 | 秒 | 出力トークン | 推論トークン | 推論文字数 | 本文に思考タグ | 本文の先頭")
    for r in results:
        if "error" in r:
            print(f"{r['variant']} | {r['sec']} | エラー: {r['error'][:80]}")
            continue
        head = r["content"].replace("\n", " ")[:40]
        print(f"{r['variant']} | {r['sec']} | {r['completion_tokens']} | {r['reasoning_tokens']} | "
              f"{r['reasoning_len']} | {r['think_marker_in_content']} | {head}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_reasoning_off_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n全文を保存しました: {out}")


if __name__ == "__main__":
    main()
