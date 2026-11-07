"""検証用にログから必要な部分だけを抜き出す（1本ごとに次の2つ）。
  1. クライマックス前後（直前・クライマックス1・2・エンディング誘導1回目）の入力とGM応答
  2. 反転・誤認の内容と、それを説明していそうなNPCの台詞（ターン番号付き）
使い方: python tools/extract_log.py "*_exp-xxx.json"  （ログのパターンを指定。省略時は今いるフォルダの *.json すべて）
出力: 今いるフォルダの log_extract.txt（標準出力にも表示）。検証では Claude にこのファイルだけを渡す
"""
import json
import re
import sys
import glob

MAX = 600  # クライマックス前後の1発言あたりの最大文字数（0で無制限）

# 種明かし・解説によく出る言い回し
MARKERS = ["実は", "だったのだ", "だったんだ", "だったのよ", "だったのです", "つまり", "ということ",
           "正体", "本当は", "真相", "真実", "偽装", "意味", "仕組", "隠して", "隠蔽", "のためだった", "ためなのだ"]


def cut(s):
    s = (s or "").strip()
    return s if not MAX or len(s) <= MAX else s[:MAX] + "…（略）"


def extract(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    st = data.get("state") or {}
    plot = st.get("plot") or {}
    h = [m for m in data.get("history", []) if m.get("role") != "system"]
    # h[0]=開始指示(user), h[1]=開始シーン(T0), 以降 user/assistant の組 → ターン1から
    turns = []
    i = 2
    while i < len(h):
        u = h[i]["content"] if h[i]["role"] == "user" else ""
        a = h[i + 1]["content"] if i + 1 < len(h) and h[i + 1]["role"] == "assistant" else ""
        turns.append((u, a))
        i += 2
    opening = h[1]["content"] if len(h) > 1 else ""
    cl = plot.get("climax") or {}
    out = [f"=== {path}", f"ジャンル: {st.get('genre', '')}",
           f"舞台(setting): {cl.get('setting', '')}", f"山場(peak): {cl.get('peak', '')}"]

    # 1. クライマックス前後
    out.append("■ クライマックス")
    e = next((n for n, (_, a) in enumerate(turns, 1) if "【エンディング】" in a), None)
    if e is None:
        out.append("※【エンディング】が見つからない（未完）")
    else:
        first_end = e - st.get("post_prompt_count", 0)
        c1 = first_end - 2
        out.append(f"エンディング=T{e} / 誘導1回目=T{first_end} / クライマックス=T{c1},T{c1 + 1}")
        labels = {c1 - 1: "直前", c1: "クライマックス1", c1 + 1: "クライマックス2", first_end: "誘導1回目"}
        for n in sorted(labels):
            if 1 <= n <= len(turns):
                u, a = turns[n - 1]
                out += [f"--- T{n}（{labels[n]}）", f"[入力] {cut(u)}", f"[GM] {cut(a)}"]

    # 2. 反転・誤認と、説明していそうな台詞
    out.append("■ 反転・誤認")
    for key, label in (("twists", "反転"), ("misconceptions", "誤認")):
        for k, it in enumerate(plot.get(key, []) or []):
            c = it.get("content", "") if isinstance(it, dict) else str(it)
            out.append(f"[{label}{k + 1}] {c}")
    hits = 0
    for n, a in [(0, opening)] + [(n, a) for n, (_, a) in enumerate(turns, 1)]:
        for ln in re.findall(r"「([^」]{6,})」", a or ""):
            if any(m in ln for m in MARKERS):
                out.append(f"T{n}: 「{ln[:200]}」")
                hits += 1
    out.append(f"（該当台詞 {hits} 件）")
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:] or ["*.json"]
    files = sorted({p for a in args for p in glob.glob(a, recursive=True)})
    if not files:
        print(f"ログが見つかりません: {args}（ログのあるフォルダで実行するか、パスを指定してください）")
        sys.exit(1)
    res = []
    for p in files:
        try:
            res.append(extract(p))
        except Exception as ex:
            res.append(f"=== {p}\n※読み込み失敗: {ex}")
    text = "\n\n".join(res)
    print(text)
    print(f"{len(files)}件を処理しました", file=sys.stderr)
    with open("log_extract.txt", "w", encoding="utf-8") as f:
        f.write(text)
