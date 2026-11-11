"""エンディング誘導の1回目と判定失敗が同じターンに重なったとき、先送りが効くかを実例で試す確認用スクリプト（ゲームは回さない）。

logs/ のログから、誘導1回目のターンで判定に失敗して [Ending] になったターンの直前までの履歴とプレイヤーの入力を取り出し、
  A：今までの方法（エンディング誘導の1回目をそのまま入れる）
  B：先送り（そのターンは「完結させず、[Ending]は出力しない」だけを入れる）
で各3回描かせる。A で [Ending] になる回数と、B で [Ending] を出さずに失敗の結果を描けるかを見る。描写の冒頭も残す。

使い方：LM Studio でモデルを1つだけロードし、サーバーを起動してから、narrative-interact のフォルダで
    python tools/check_ending_fail_probe.py
結果を tools/check_ending_fail_probe_result.txt に保存する（そのファイルを貼ってもらえれば判断できる）。
"""
import glob
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TOOLS_DIR))
import lang as _lang  # noqa: E402
import api  # noqa: E402
import main  # noqa: E402

# 誘導1回目で判定に失敗し、そのターンで [Ending] になった実例（ファイル名の一部, T番号）
TARGETS = [("銀の巡礼路", 12), ("Embered_Relic", 13), ("Veiled_Rot", 12)]
TRIES = 3


def load_case(key, n):
    files = sorted(p for p in glob.glob(os.path.join("logs", "*.json")) if key in os.path.basename(p))
    if not files:
        return None
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    st = data.get("state") or {}
    hist = data.get("history") or []
    if len(hist) < 2 * n + 2:
        return None
    msgs = [dict(m) for m in hist[:2 * n + 2]]  # system … Tn の入力まで
    return os.path.basename(files[0]), st.get("lang", "ja"), st.get("plot") or {}, msgs


def main_():
    lines = []
    total = {"A": [0, 0], "B": [0, 0]}
    for key, n in TARGETS:
        case = load_case(key, n)
        if not case:
            lines.append(f"－ {key} T{n}: ログが見つからない（logs/ にあるか確認）")
            continue
        fname, lg, plot, msgs = case
        _lang.LANG = lg
        action = msgs[-1]["content"].split("\n")[0].strip()
        lines.append(f"=== {fname[:45]} T{n} / 入力: {action[:60]}")
        for name, inj in (("A", main._ending_first_injection(plot)), ("B", main._ENDING_DEFER_INJECTION)):
            label = "A 誘導をそのまま入れる" if name == "A" else "B 先送り"
            ends = 0
            for k in range(TRIES):
                m2 = [dict(m) for m in msgs]
                m2[-1]["content"] += f"\n（GMへの場面指示: {inj}）"
                reply = main._normalize_ending_marker(api.chat(m2))
                end = main.ENDING_MARKER in reply
                ends += end
                lines.append(f"  [{label}] {k + 1}回目: {'[Ending]あり' if end else '続く'} / 冒頭: "
                             + reply[:200].replace("\n", " "))
                if end:
                    lines.append("      末尾: " + reply[-200:].replace("\n", " "))
                print(f"{key} T{n} [{label}] {k + 1}/{TRIES}: {'Ending' if end else '続く'}", file=sys.stderr)
            total[name][0] += ends
            total[name][1] += TRIES
            lines.append(f"  [{label}] [Ending] {ends}/{TRIES}")
    lines += ["", f"合計 [A 誘導をそのまま入れる] [Ending] {total['A'][0]}/{total['A'][1]}",
              f"合計 [B 先送り] [Ending] {total['B'][0]}/{total['B'][1]}"]
    text = "\n".join(lines)
    print(text)
    out = os.path.join(TOOLS_DIR, "check_ending_fail_probe_result.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"保存しました: {out}", file=sys.stderr)


if __name__ == "__main__":
    main_()
