"""検証用にログから必要な部分だけを抜き出す（1本ごとに次の2つ）。
  1. strong：クライマックス前後（直前・クライマックス1・2・エンディング誘導1回目）の入力とGM応答
     adaptive：逸脱と判定したターン・新プロット・警告注入／再生成前後のターン、および終盤（エンディングとその直前）
     off / improv：終盤（エンディングとその直前）
     英語のログ（lang=en）は、you と主人公の名前の回数・比喩の件数・Markdown の消し残り・開始シーンも出す
     日本語のログは、比較用に比喩の件数（まるで・かのよう・のように・のような）を出す
  2. 反転・誤認の内容と、それを説明していそうなNPCの台詞（ターン番号付き）
使い方: python tools/extract_log.py "*_exp-xxx.json"  （ログのパターンを指定。省略時は今いるフォルダの *.json すべて）
出力: tools/log_extract.txt（標準出力にも表示）。検証では Claude にこのファイルだけを渡す
"""
import json
import re
import sys
import glob
import os

MAX = 600  # クライマックス前後の1発言あたりの最大文字数（0で無制限）

# 種明かし・解説によく出る言い回し
MARKERS = ["実は", "だったのだ", "だったんだ", "だったのよ", "だったのです", "つまり", "ということ",
           "正体", "本当は", "真相", "真実", "偽装", "意味", "仕組", "隠して", "隠蔽", "のためだった", "ためなのだ"]
MARKERS_EN = ["actually", "all along", "the truth", "in truth", "really was", "was never", "it means",
              "that means", "which means", "the reason", "was meant", "hidden", "secret", "designed", "never been"]
SIMILES_EN = re.compile(r"\b(like an?|as if|as though)\b", re.I)
SIMILES_JA = re.compile(r"まるで|かのよう|のように|のような|のごとく|の如く")  # 日英比較用（英語の like a / as if に相当）


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
    mode = st.get("plot_mode", "")
    cl = plot.get("climax") or {}
    en = st.get("lang") == "en"
    out = [f"=== {path}", f"モード: {mode} / ジャンル: {st.get('genre', '')} / タイトル: {st.get('title', '')}"
                          f" / 言語: {st.get('lang', 'ja')} / 総ターン: {len(turns)}"]
    if en:
        # 英語版の確認：人称・比喩・消し残りの Markdown
        gm = [opening] + [a for _, a in turns]
        name = ((plot.get("protagonist") or {}).get("name") or "").split(" ")[0]
        you = sum(len(re.findall(r"\byou\b", a or "", re.I)) for a in gm)
        nm = sum(len(re.findall(rf"\b{re.escape(name)}\b", a or "")) for a in gm) if name else 0
        sim = [len(SIMILES_EN.findall(a or "")) for a in gm]
        md = [n for n, a in enumerate(gm) if re.search(r"\*[^*\n]+\*|^\s*(#|[-*] |\d+\. )", a or "", re.M)]
        out += [f"■ 英語：you {you} 回 / 主人公の名前（{name or '不明'}）{nm} 回",
                f"比喩（like a / as if / as though）: 計 {sum(sim)} 件・1ターン平均 {sum(sim) / max(len(gm), 1):.1f}",
                f"Markdown の消し残り: {['T' + str(n) for n in md] or 'なし'}",
                f"舞台の確認用 開始シーン: {cut(opening)[:300]}"]
    else:
        gm = [opening] + [a for _, a in turns]
        sim = [len(SIMILES_JA.findall(a or "")) for a in gm]
        out.append(f"比喩（まるで / かのよう / のように / のような）: 計 {sum(sim)} 件・1ターン平均 {sum(sim) / max(len(gm), 1):.1f}")
    marks = ("[Ending]", "【エンディング】", "[エンディング]", "［エンディング］")  # 新旧の終わりの印
    e = next((n for n, (_, a) in enumerate(turns, 1) if any(m in a for m in marks)), None)

    def show(labels):
        for n in sorted(labels):
            if 1 <= n <= len(turns):
                u, a = turns[n - 1]
                out.extend([f"--- T{n}（{labels[n]}）", f"[入力] {cut(u)}", f"[GM] {cut(a)}"])

    if mode == "strong":
        # 1. クライマックス前後
        out += [f"舞台(setting): {cl.get('setting', '')}", f"山場(peak): {cl.get('peak', '')}", "■ クライマックス"]
        if e is None:
            out.append("※終わりの印（[Ending]／【エンディング】）が見つからない（未完）")
        else:
            first_end = e - st.get("post_prompt_count", 0)
            c1 = first_end - 2
            out.append(f"エンディング=T{e} / 誘導1回目=T{first_end} / クライマックス=T{c1},T{c1 + 1}")
            if "warp_retries" in st:
                out.append(f"強制移動の描き直し: {st['warp_retries'] or 'なし'}")
            show({c1 - 1: "直前", c1: "クライマックス1", c1 + 1: "クライマックス2", first_end: "誘導1回目"})
    else:
        # 1. 逸脱・再生成（adaptive）と終盤
        labels = {}
        if mode == "adaptive":
            out.append("■ 逸脱・再生成")
            dt = st.get("deviation_turns")
            out.append(f"逸脱と判定したターン: {dt if dt is not None else '（記録なし：古い版のログ）'}"
                       f" / 最大累積: {st.get('peak_deviation_count', 0)} / 再生成: {st.get('adaptive_replotted', False)}")
            np_ = st.get("adaptive_new_plot") or {}
            if np_:
                out += [f"[新・目標] {np_.get('protagonist_goal', '')}",
                        f"[新・クライマックス] {np_.get('climax_situation', '')}",
                        f"[新・着地点] {np_.get('ending_scene', '')}"]
                for b in np_.get("beats", []) or []:
                    if isinstance(b, dict):
                        out.append(f"[新・ビート] {b.get('timing', '')}: {b.get('description', '')}")
            # 全ターンのプレイヤー入力（1行目のみ・判定タグを除く）。逸脱判定の印付き
            dts = set(dt or [])
            for n, (u, _) in enumerate(turns, 1):
                first = (u or "").split("\n")[0].strip()
                out.append(f"{'★' if n in dts else '　'}T{n}: {first[:80]}")
            if dt and len(dt) >= 3:
                labels[dt[2]] = "警告注入（累積3）"
            if dt and len(dt) >= 5:
                r = dt[4]
                labels.update({r - 1: "再生成の直前", r: "再生成（新ビート注入）", r + 1: "再生成の次"})
        out.append("■ 終盤")
        if e is None:
            out.append("※終わりの印（[Ending]／【エンディング】）が見つからない（未完）")
        else:
            out.append(f"エンディング=T{e} / 誘導回数={st.get('post_prompt_count', 0)}")
            labels.update({e - 1: "エンディングの直前", e: "エンディング"})
        show(labels)

    # 2. 反転・誤認と、説明していそうな台詞
    out.append("■ 反転・誤認")
    for key, label in (("twists", "反転"), ("misconceptions", "誤認")):
        for k, it in enumerate(plot.get(key, []) or []):
            c = it.get("content", "") if isinstance(it, dict) else str(it)
            out.append(f"[{label}{k + 1}] {c}")
    hits = 0
    for n, a in [(0, opening)] + [(n, a) for n, (_, a) in enumerate(turns, 1)]:
        if en:
            for ln in re.findall(r"[\"“]([^\"”]{6,})[\"”]", a or ""):
                if any(m in ln.lower() for m in MARKERS_EN):
                    out.append(f'T{n}: "{ln[:200]}"')
                    hits += 1
            continue
        for ln in re.findall(r"「([^」]{6,})」", a or ""):
            if any(m in ln for m in MARKERS):
                out.append(f"T{n}: 「{ln[:200]}」")
                hits += 1
    out.append(f"（該当台詞 {hits} 件）")
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:] or ["logs/*.json"]
    files = set()
    for a in args:
        hit = glob.glob(a, recursive=True)
        if not hit and not a.startswith("logs"):
            hit = glob.glob("logs/" + a, recursive=True)  # ログは logs/ に保存される
        files.update(hit)
    files = sorted(files)
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
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log_extract.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"保存しました: {out_path}", file=sys.stderr)
