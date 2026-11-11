"""強制移動の描き直しが効くかを、実際に強制移動が起きたターンで試す確認用スクリプト（ゲームは回さない）。

logs/ のログから、強制移動が起きたターンの直前までの履歴とプレイヤーの入力を取り出し、
クライマックスの注入文を付け直して、描き直しの2つの方法で各3回描き直させ、強制移動の判定（api.check_warp）にかける。
  A：前の方法（注入文の舞台の指定を残したまま、描き直しの指示を添える）
  B：今の方法（注入文から舞台の指定を外して、描き直しの指示を添える）

使い方：LM Studio でモデルを1つだけロードし、サーバーを起動してから、narrative-interact のフォルダで
    python tools/check_warp_retry_probe.py
結果を tools/check_warp_retry_probe_result.txt に保存する（そのファイルを貼ってもらえれば判断できる）。
"""
import glob
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TOOLS_DIR))
import lang as _lang  # noqa: E402
import beat as beat_mod  # noqa: E402
import api  # noqa: E402
import main  # noqa: E402

# 強制移動が起きたターン（ファイル名の一部, T番号）。いずれもクライマックス1回目
TARGETS = [
    ("偽りの箱庭", 11), ("残響の境界線", 11), ("残響の断罪", 11),
    ("蒼穹の旅路", 11), ("鳴り止まぬ葬列", 10), ("Hollow_Whispers", 10),
]
TRIES = 3
METHODS = [("A 舞台の指定を残す", False), ("B 舞台の指定を外す", True)]


def load_case(key, n):
    files = sorted(p for p in glob.glob(os.path.join("logs", "*.json")) if key in os.path.basename(p))
    if not files:
        return None
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    st = data.get("state") or {}
    hist = data.get("history") or []
    # history: [system, 開始指示, 開始シーン, T1入力, T1応答, ...] → Tn の入力は index 2n+1
    if len(hist) < 2 * n + 2:
        return None
    msgs = [dict(m) for m in hist[:2 * n + 2]]
    cl = (st.get("plot") or {}).get("climax") or {}
    inj = beat_mod._TEMPLATES["climax"].format(setting=cl.get("setting", ""),
                                              conflict_type=cl.get("conflict_type", ""),
                                              peak=cl.get("peak", ""))
    msgs[-1]["content"] += f"\n（GMへの場面指示: {inj}）"
    prev = hist[2 * n]["content"]
    action = hist[2 * n + 1]["content"].split("\n")[0].strip()
    return os.path.basename(files[0]), st.get("lang", "ja"), msgs, prev, action


def main_():
    lines = []
    total = {name: [0, 0] for name, _ in METHODS}
    for key, n in TARGETS:
        case = load_case(key, n)
        if not case:
            lines.append(f"－ {key} T{n}: ログが見つからない（logs/ にあるか確認）")
            continue
        fname, lg, msgs, prev, action = case
        _lang.LANG = lg
        lines.append(f"=== {fname[:45]} T{n} / 入力: {action[:60]}")
        for name, strip in METHODS:
            res = []
            for k in range(TRIES):
                reply = api.chat(main._warp_retry_messages(msgs, strip_setting=strip))
                warp = api.check_warp(prev, action, reply)
                res.append(warp)
                total[name][0] += warp
                total[name][1] += 1
                lines.append(f"  [{name}] {k + 1}回目: {'強制移動あり' if warp else 'なし'} / 冒頭: "
                             + reply[:150].replace("\n", " "))
                print(f"{key} T{n} [{name}] {k + 1}/{TRIES}: {'yes' if warp else 'no'}", file=sys.stderr)
            lines.append(f"  [{name}] 強制移動 {sum(res)}/{TRIES}")
    lines.append("")
    for name, (w, t) in total.items():
        lines.append(f"合計 [{name}] 強制移動 {w}/{t}")
    text = "\n".join(lines)
    print(text)
    out = os.path.join(TOOLS_DIR, "check_warp_retry_probe_result.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"保存しました: {out}", file=sys.stderr)


if __name__ == "__main__":
    main_()
