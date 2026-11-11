"""山場の代行（プレイヤーの入力にない主人公の行動で、GMが山場を果たしてしまう）を、LLMが yes/no で見分けられるかを調べる確認用スクリプト。

logs/ の strong のログから、クライマックス1回目からエンディングまでのターンを取り出し、
山場（climax.peak）・プレイヤーの行動・今回の描写を渡して判定させる。ゲームは回さない（既存のログだけを使う）。

使い方：LM Studio でモデルを1つだけロードし、サーバーを起動してから、narrative-interact のフォルダで
    python tools/check_peak_probe.py                         # logs/*.json の strong すべて
    python tools/check_peak_probe.py "logs/*_20261111_*.json"  # パターン指定
結果を tools/check_peak_probe_result.txt に保存する（そのファイルを貼ってもらえれば判断できる）。
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

# 目視で確かめた正解（ファイル名の一部, T番号）: True=代行あり, False=代行なし, None=判断が分かれる
LABELS = {
    ("Silented_Crown", 13): True,    # 「羊皮紙の端をつかむ」だけで、GMが署名させる
    ("Silented_Crown", 11): False, ("Silented_Crown", 12): False,
    ("銀河の残響", 13): True,        # 11/10。「キーパッドに手を置く」だけで、GMが「意図した入力を施す」
    ("銀河の残響", 11): False, ("銀河の残響", 12): False,
    ("Echos_of_Dawn", 12): True,     # 11/10。「槌を高く掲げる」だけで、GMが振り下ろして鐘を鳴らす
    ("Echos_of_Dawn", 10): False, ("Echos_of_Dawn", 11): False,
    ("Broken_Ledger", 15): None,     # 手首を振りほどいたあと、GMが門を走り抜けさせる（逃走の山場）
    ("Broken_Ledger", 12): False, ("Broken_Ledger", 13): False, ("Broken_Ledger", 14): False,
    ("鋼の揺籃", 14): None,          # 端子へ歩み寄るだけで、GMがケーブルを挿し込ませる
    ("放課後の残響", 12): None,      # スクリプトを手に取るだけで、GMが頷かせる（決定の山場）
    ("嘘の標本", 11): False, ("嘘の標本", 12): False, ("嘘の標本", 13): False,
    ("虚飾の境界線", 11): False, ("虚飾の境界線", 12): False, ("虚飾の境界線", 13): False,
    ("残響の断罪", 11): False, ("残響の断罪", 12): False, ("残響の断罪", 13): False,
    ("Neon_Pulse", 12): False, ("Neon_Pulse", 13): False, ("Neon_Pulse", 14): False,
    ("Pale_Threshold", 10): False, ("Pale_Threshold", 11): False, ("Pale_Threshold", 12): False,
    ("Soft_Echoes", 11): False, ("Soft_Echoes", 12): False, ("Soft_Echoes", 13): False,
    ("銀の巡礼路", 10): False, ("銀の巡礼路", 11): False, ("銀の巡礼路", 12): False,  # 12 は NPC が果たす（別の問題）
    ("残響の境界線", 11): False, ("残響の境界線", 12): False,
    ("残響の境界線", 13): None,      # 結晶へ跳躍した結果として核に触れる
}


def build_prompt(peak, act, cur):
    return (
        "以下はテキストRPGの1場面です。\n\n"
        f"【山場（物語の設計上、主人公が取るはずの行動）】\n{peak}\n\n"
        f"【プレイヤーの行動】\n{act}\n\n"
        f"【今回の描写】\n{cur[:2500]}\n\n"
        "今回の描写で、主人公は、プレイヤーの行動に書かれていない自分の行動によって山場を果たしていますか。"
        "プレイヤーの行動そのもの、またはその直接の結果として山場に至っただけなら no。"
        "主人公以外の人物が山場を果たした場合も no。"
        "山場と関係のない主人公の動作（立つ・見つめる・息を整える等）だけなら no。\n"
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
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return f"[ERROR {e}]"
    return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


def cases(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    st = data.get("state") or {}
    if st.get("plot_mode") != "strong":
        return []
    peak = ((st.get("plot") or {}).get("climax") or {}).get("peak", "")
    h = [m for m in data.get("history", []) if m.get("role") != "system"]
    turns = []
    i = 2
    while i < len(h):
        u = h[i]["content"] if h[i]["role"] == "user" else ""
        a = h[i + 1]["content"] if i + 1 < len(h) and h[i + 1]["role"] == "assistant" else ""
        turns.append((u, a))
        i += 2
    marks = ("[Ending]", "【エンディング】", "[エンディング]", "［エンディング］")
    e = next((n for n, (_, a) in enumerate(turns, 1) if any(m in a for m in marks)), None)
    if e is None or not peak:
        return []
    first_end = e - st.get("post_prompt_count", 0)
    c1 = first_end - 2 - (1 if st.get("ending_deferred") else 0)
    return [(n, peak, (turns[n - 1][0] or "").split("\n")[0].strip(), turns[n - 1][1])
            for n in range(max(c1, 1), e + 1)]


def main():
    pats = sys.argv[1:] or ["logs/*.json"]
    files = sorted({p for pat in pats for p in glob.glob(pat)})
    lines, ok, ng = [], 0, 0
    for p in files:
        name = os.path.basename(p)
        for n, peak, act, cur in cases(p):
            ans = ask(build_prompt(peak, act, cur)).strip()
            yes = ans.lower().startswith("yes")
            label = next((v for (k, t), v in LABELS.items() if k in name and t == n), "?")
            mark = "" if label in ("?", None) else ("○" if yes == label else "×")
            ok += mark == "○"
            ng += mark == "×"
            exp = {True: "代行あり", False: "代行なし", None: "判断が分かれる", "?": "未確認"}[label]
            row = f"{mark or '－'} {name[:40]} T{n}: 判定={'yes' if yes else 'no'}（生: {ans!r}） 正解={exp} / 入力: {act[:60]}"
            print(row, file=sys.stderr)
            lines.append(row)
            if yes or label in ("?", None):
                lines.append(f"    山場: {peak[:80]}")
                lines.append("    今回の描写の冒頭: " + cur[:300].replace("\n", " "))
    lines.append(f"\n正解が分かっているもの: 一致 {ok} / 不一致 {ng}")
    text = "\n".join(lines)
    print(text)
    out = os.path.join(TOOLS_DIR, "check_peak_probe_result.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"保存しました: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
