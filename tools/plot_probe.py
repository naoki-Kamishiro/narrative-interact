"""プロット生成だけを繰り返して、修復（[plot修復]）の頻度を日英で比べる確認用スクリプト。

本番と同じ plot.generate を呼ぶ（ジャンルはバッチ用の一覧、タイトルは本番と同じ生成）。
使い方：LM Studio を起動してから、narrative-interact のフォルダで
    python tools/plot_probe.py               # 日英それぞれ5本（同じジャンルの並びで交互に）
    python tools/plot_probe.py 10            # 日英それぞれ10本
    python tools/plot_probe.py 10 en         # 英語だけ10本（ja / en / both）
出力（tools/ に保存）：
    plot_probe_summary.txt  … 集計（これだけ貼ってもらえば判断できる）
    plot_probe_raw.json     … LLMの生の出力を含む全記録（必要なときだけ）
"""
import json
import os
import random
import re
import sys
from collections import Counter

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TOOLS_DIR))

import lang as _lang  # noqa: E402
import plot as plot_mod  # noqa: E402
import api  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
WHICH = sys.argv[2] if len(sys.argv) > 2 else "both"
LANGS = ["ja", "en"] if WHICH == "both" else [WHICH]

GENRES_JA = ["ホラー", "ミステリー", "ファンタジー", "SF", "時代劇", "現代ドラマ",
             "サスペンス", "青春", "怪談", "冒険", "犯罪", "日常"]
GENRES_EN = ["Horror", "Mystery", "Fantasy", "Sci-Fi", "Historical", "Contemporary drama",
             "Suspense", "Coming-of-age", "Ghost story", "Adventure", "Crime", "Slice of life"]
BEAT_KEYS = ("misconceptions", "failures", "twists", "conflicts")
REQUIRED = ("protagonist", "characters", "climax", "ending", "ending_note", "choices") + BEAT_KEYS

# 生の出力を横取りして記録する（本番の処理はそのまま）
_raws: list = []
_orig_chat_json = plot_mod.chat_json


def _spy(messages):
    raw = _orig_chat_json(messages)
    _raws.append(raw)
    return raw


plot_mod.chat_json = _spy


def inspect_raw(raw: str) -> dict:
    """生の出力の形を調べる：トップレベルの欠落キーと、choices の中に入り込んだキー"""
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        d = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        try:
            d = json.loads(m.group(0)) if m else None
        except Exception:
            d = None
    if not isinstance(d, dict):
        return {"parse": False}
    nested = set()
    for c in d.get("choices") or []:
        if isinstance(c, dict):
            nested |= {k for k in c if k in REQUIRED}
    return {"parse": True,
            "missing_top": [k for k in REQUIRED if k not in d],
            "nested_in_choices": sorted(nested)}


order = random.sample(range(len(GENRES_JA)), len(GENRES_JA))
records = []
for i in range(N):
    gi = order[i % len(order)]
    for lg in LANGS:
        _lang.LANG = lg
        genre = GENRES_EN[gi] if lg == "en" else GENRES_JA[gi]
        t = api.generate_genre_title(genre)
        title = (t.get("title") or "").strip() or ("Untitled" if lg == "en" else "無題")
        _raws.clear()
        plot = plot_mod.generate(genre, title)
        rec = {
            "lang": lg, "genre": genre, "title": title,
            "ok": bool(plot),
            "attempts": plot_mod.LAST_GEN["attempts"],
            "repairs": list(plot_mod.LAST_GEN["repairs"]),
            "raw_shape": [inspect_raw(r) for r in _raws],
            "raw": list(_raws),
        }
        records.append(rec)
        print(f"[{lg}] {i + 1}/{N} {genre} / {title}: 試行{rec['attempts']} 修復{len(rec['repairs'])}"
              f" {rec['raw_shape'][-1] if rec['raw_shape'] else ''}", file=sys.stderr)

# 集計
lines = []
for lg in LANGS:
    rs = [r for r in records if r["lang"] == lg]
    if not rs:
        continue
    rep_kinds = Counter(re.sub(r"\d+", "N", m) for r in rs for m in r["repairs"])
    nested = Counter(k for r in rs for sh in r["raw_shape"] for k in sh.get("nested_in_choices", []))
    missing = Counter(k for r in rs for sh in r["raw_shape"] for k in sh.get("missing_top", []))
    lines += [
        f"■ {lg}（{len(rs)}本）",
        f"失敗（プロットなし）: {sum(not r['ok'] for r in rs)}",
        f"再試行あり: {sum(r['attempts'] > 1 for r in rs)}",
        f"修復あり: {sum(bool(r['repairs']) for r in rs)}",
        f"パース不能の出力: {sum(not sh.get('parse') for r in rs for sh in r['raw_shape'])}",
        "修復の内容: " + (", ".join(f"{k}×{v}" for k, v in rep_kinds.most_common()) or "なし"),
        "生の出力で choices の中に入り込んだキー: " + (", ".join(f"{k}×{v}" for k, v in nested.most_common()) or "なし"),
        "生の出力でトップレベルに無いキー: " + (", ".join(f"{k}×{v}" for k, v in missing.most_common()) or "なし"),
        "",
    ]
    for r in rs:
        lines.append(f"  {r['genre']} / {r['title']}: 試行{r['attempts']} 修復{len(r['repairs'])}"
                     + (f" {r['repairs']}" if r["repairs"] else ""))
    lines.append("")

text = "\n".join(lines)
print(text)
with open(os.path.join(TOOLS_DIR, "plot_probe_summary.txt"), "w", encoding="utf-8") as f:
    f.write(text)
with open(os.path.join(TOOLS_DIR, "plot_probe_raw.json"), "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=1)
print("保存しました: tools/plot_probe_summary.txt / tools/plot_probe_raw.json", file=sys.stderr)
