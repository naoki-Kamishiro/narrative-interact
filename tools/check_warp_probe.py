"""クライマックスの強制移動（主人公が移動の行動なしに別の場所へ移る）を、LLMが yes/no で見分けられるかを調べる確認用スクリプト。

logs/ の strong のログから、クライマックスの2ターン（1回目・2回目）を取り出し、
直前の描写・プレイヤーの行動・今回の描写を渡して判定させる。ゲームは回さない（既存のログだけを使う）。

使い方：LM Studio でモデルを1つだけロードし、サーバーを起動してから、narrative-interact のフォルダで
    python tools/check_warp_probe.py                         # logs/*.json の strong すべて
    python tools/check_warp_probe.py "logs/*_20261111_*.json"  # パターン指定
結果を tools/check_warp_probe_result.txt に保存する（そのファイルを貼ってもらえれば判断できる）。
"""
import glob
import json
import os
import sys
import urllib.error
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TOOLS_DIR))
from config import LM_STUDIO_URL, API_KEY  # noqa: E402

URL = LM_STUDIO_URL.rstrip("/") + "/chat/completions"

# 11/10〜11/11 のログで目視で確かめた正解（ファイル名の一部, ターン）: True=強制移動あり, None=不明
LABELS = {
    ("偽りの箱庭", 11): True,
    ("残響の境界線", 11): True,
    ("Hollow_Whispers", 10): True,
    ("銀河の残響", 11): True,   # 11/10 のログ。信号の場所を確かめただけでサーバー室へ到達
    ("銀河の残響", 12): False,
    ("Faded_Horizon", 12): None,
    ("Faded_Horizon", 13): None,
    ("偽りの箱庭", 12): False,
    ("残響の境界線", 12): False,
    ("Hollow_Whispers", 11): False,
    ("呪詛の揺り籠", 11): False, ("呪詛の揺り籠", 12): False,
    ("沈黙の証言者", 11): False, ("沈黙の証言者", 12): False,
    ("淡い夜の余白", 11): False, ("淡い夜の余白", 12): False,
    ("Embered_Relic", 11): False, ("Embered_Relic", 12): False,
    ("Ironed_Decree", 12): False, ("Ironed_Decree", 13): False,
    ("Mixed_Signals", 10): False, ("Mixed_Signals", 11): False,
    ("Veiled_Rot", 10): False, ("Veiled_Rot", 11): False,
}


def build_prompt(prev, act, cur):
    return (
        "以下はテキストRPGの連続する場面です。\n\n"
        f"【直前の描写】\n{prev[-600:]}\n\n"
        f"【プレイヤーの行動】\n{act}\n\n"
        f"【今回の描写】\n{cur[:1200]}\n\n"
        "今回の描写で、主人公は直前の描写と別の場所へ移っていますか。"
        "プレイヤーの行動が歩く・進む・入るなどの移動で、その行き先に普通に着いただけなら no。"
        "崩落・光・空間の歪み・視界の一変などで、移動の行動なしに、または一瞬で遠く離れた場所へ移ったなら yes。"
        "同じ場所のまま風景や状況が変わっただけなら no。\n"
        "「yes」か「no」の1単語のみで答えてください。"
    )


def ask(prompt):
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": "あなたはテキストRPGの進行を補助するシステムです。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4,
        "temperature": 0.0,
        "reasoning_effort": "none",
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return f"[ERROR {e}]"
    return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


def climax_cases(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    st = data.get("state") or {}
    if st.get("plot_mode") != "strong":
        return []
    h = [m for m in data.get("history", []) if m.get("role") != "system"]
    opening = h[1]["content"] if len(h) > 1 else ""
    turns = []
    i = 2
    while i < len(h):
        u = h[i]["content"] if h[i]["role"] == "user" else ""
        a = h[i + 1]["content"] if i + 1 < len(h) and h[i + 1]["role"] == "assistant" else ""
        turns.append((u, a))
        i += 2
    marks = ("[Ending]", "【エンディング】", "[エンディング]", "［エンディング］")
    e = next((n for n, (_, a) in enumerate(turns, 1) if any(m in a for m in marks)), None)
    if e is None:
        return []
    c1 = e - st.get("post_prompt_count", 0) - 2
    out = []
    for n in (c1, c1 + 1):
        if 1 <= n <= len(turns):
            prev = turns[n - 2][1] if n >= 2 else opening
            act = (turns[n - 1][0] or "").split("\n")[0].strip()
            out.append((n, prev, act, turns[n - 1][1]))
    return out


def main():
    pats = sys.argv[1:] or ["logs/*.json"]
    files = sorted({p for pat in pats for p in glob.glob(pat)})
    lines, ok, ng = [], 0, 0
    for p in files:
        name = os.path.basename(p)
        for n, prev, act, cur in climax_cases(p):
            ans = ask(build_prompt(prev, act, cur)).strip()
            yes = ans.lower().startswith("yes")
            label = next((v for (k, t), v in LABELS.items() if k in name and t == n), "?")
            mark = "" if label in ("?", None) else ("○" if yes == label else "×")
            if mark == "○":
                ok += 1
            elif mark == "×":
                ng += 1
            exp = {True: "移動あり", False: "移動なし", None: "不明", "?": "未確認"}[label]
            row = f"{mark or '－'} {name[:40]} T{n}: 判定={'yes' if yes else 'no'}（生: {ans!r}） 正解={exp} / 入力: {act[:60]}"
            print(row, file=sys.stderr)
            lines.append(row)
            if yes or label in ("?", None):
                lines.append("    今回の描写の冒頭: " + cur[:200].replace("\n", " "))
    lines.append(f"\n正解が分かっているもの: 一致 {ok} / 不一致 {ng}")
    text = "\n".join(lines)
    print(text)
    out = os.path.join(TOOLS_DIR, "check_warp_probe_result.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"保存しました: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
