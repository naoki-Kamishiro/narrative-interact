"""
プロット生成モジュール。
プロットはimmutable（不変）扱い。更新は圧縮フェーズのみ。
"""

import json
import re
import sys
from json_repair import repair_json
from api import chat_json
from prompt import SYSTEM_PLOT, build_plot_message
from display import system_print

DEBUG_MODE: bool = False

MAX_RETRIES = 3

def generate(genre: str, title: str) -> dict:
    system_print("プロットを生成中...")
    messages = [
        {"role": "system", "content": SYSTEM_PLOT},
        {"role": "user",   "content": build_plot_message(genre, title)},
    ]
    for attempt in range(1, MAX_RETRIES + 1):
        raw = chat_json(messages)
        result = _parse(raw)
        if result and all(result.get(k) for k in ("ending", "protagonist", "characters", "climax")):
            system_print("プロット生成完了")
            _warn_missing_keys(result)
            return result
        if attempt < MAX_RETRIES:
            missing = [k for k in ("ending", "protagonist", "characters", "climax") if not result.get(k)] if result else ["parse"]
            system_print(f"再試行中... ({attempt}/{MAX_RETRIES}) 不足: {', '.join(missing)}")
    system_print("プロット生成に失敗しました。プロットなしで続行します。")
    return {}

def _parse(raw: str) -> dict:
    if raw.startswith("[ERROR"):
        system_print("プロット生成中にエラーが発生しました")
        return {}

    cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()
    cleaned = re.sub(r"```", "", cleaned).strip()

    # まず通常のJSON解析を試みる
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return _validate_and_repair(result)
    except json.JSONDecodeError:
        pass

    # 解析に失敗した場合、軽微な構文ミス（クォート欠落・末尾カンマ等）の
    # 自動修復を試みる
    try:
        repaired = repair_json(cleaned)
        result = json.loads(repaired)
        if isinstance(result, dict):
            return _validate_and_repair(result)
    except Exception:
        pass

    system_print("プロットのJSON解析に失敗しました")
    return {}


# choicesの中にネストされうるキー
_NESTED_KEYS = ("misconceptions", "failures", "twists", "conflicts", "climax", "characters")

_REQUIRED_KEYS = ("ending", "protagonist", "characters", "climax")

def _warn_missing_keys(plot: dict) -> None:
    """必須キーが空または欠落していた場合に警告を出す。"""
    for key in _REQUIRED_KEYS:
        val = plot.get(key)
        if not val:
            system_print(f"[警告] プロットの必須キー「{key}」が空です。物語の進行に影響する可能性があります。")


def _validate_and_repair(plot: dict) -> dict:
    """
    choicesの要素に他のビートキーがネストされている場合、
    トップレベルに引き上げて構造を修復する。
    """
    _TOP_LEVEL_LIST_KEYS = ("misconceptions", "failures", "choices", "twists", "characters")

    extracted: dict[str, list] = {k: [] for k in _NESTED_KEYS}
    repaired = False

    choices = plot.get("choices", [])
    clean_choices = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        nested_found = False
        for key in _NESTED_KEYS:
            if key in item and isinstance(item[key], list):
                extracted[key].extend(item[key])
                nested_found = True
        # choiceとして有効なキーが残っているかチェック
        valid_keys = {"description", "cost", "timing", "outcome", "label", "name", "content"}
        has_valid = any(k in item for k in valid_keys)
        if has_valid:
            # ネストキーを除いたクリーンなchoiceを残す
            clean_item = {k: v for k, v in item.items() if k not in _NESTED_KEYS}
            clean_choices.append(clean_item)
        if nested_found:
            repaired = True

    if repaired:
        plot["choices"] = clean_choices
        for key in _NESTED_KEYS:
            if extracted[key]:
                existing = plot.get(key, [])
                if not isinstance(existing, list):
                    existing = []
                plot[key] = existing + extracted[key]
                if DEBUG_MODE:
                    print(f"[plot修復] {key} を {len(extracted[key])} 件トップレベルに移動しました", file=sys.stderr)

    # protagonist が文字列など dict でない場合は dict に変換
    if not isinstance(plot.get("protagonist"), dict):
        raw_prot = plot.get("protagonist", "")
        plot["protagonist"] = {"name": str(raw_prot) if raw_prot else "", "wound": "", "goal_surface": "", "goal_deep": ""}

    # characters の各要素が dict でない場合はスキップできる形に変換
    chars = plot.get("characters", [])
    if isinstance(chars, list):
        plot["characters"] = [c if isinstance(c, dict) else {"name": str(c)} for c in chars]

    # リスト系フィールドが dict でない場合は空リストに
    for list_key in ("misconceptions", "failures", "twists", "choices"):
        val = plot.get(list_key)
        if val is not None and not isinstance(val, list):
            plot[list_key] = []
        elif isinstance(val, list):
            # 要素が dict でない場合は除外
            plot[list_key] = [item for item in val if isinstance(item, dict)]

    # climax・ending・ending_noteの欠落補完
    if not isinstance(plot.get("climax"), dict):
        plot["climax"] = {}
    climax = plot["climax"]
    # フィールドが全て空の場合、他のplot情報から最低限の内容を補完する
    if not any(climax.get(k) for k in ("setting", "conflict_type", "loss", "gain", "peak")):
        protagonist = plot.get("protagonist", {})
        conflicts = plot.get("conflicts", [])
        twists = plot.get("twists", [])
        risks = plot.get("risks", {})
        main_conflict = next((c.get("content", "") for c in conflicts if isinstance(c, dict) and c.get("type") == "メイン"), "")
        final_twist = twists[-1].get("content", "") if twists and isinstance(twists[-1], dict) else ""
        climax["setting"] = climax.get("setting") or "物語の最深部"
        climax["conflict_type"] = climax.get("conflict_type") or main_conflict or "主要な対立の決着"
        climax["loss"] = climax.get("loss") or main_conflict or ""
        climax["gain"] = climax.get("gain") or protagonist.get("goal_surface") or ""
        climax["peak"] = climax.get("peak") or final_twist or "物語の転換点"
        plot["climax"] = climax
        if DEBUG_MODE:
            print("[plot修復] climax が空だったため他フィールドから補完しました", file=sys.stderr)
    # ending が dict / list で返った場合は文字列に正規化する
    # （そのままだと GMへのプロンプトに {'scene_description': ...} のような表記が入る）
    # dict の中に ending_note 相当（フック回収・テーマの決着）が混ざっている場合は ending_note へ振り分け、
    # 着地点の情景だけを ending に残す（混ざったままだと「完全解決（…）」「余韻を残す」が着地点に入る）
    ending = plot.get("ending")
    if isinstance(ending, dict):
        note = plot.get("ending_note") if isinstance(plot.get("ending_note"), dict) else {}
        note = dict(note)
        scene_vals = []
        for k, v in ending.items():
            key = str(k).lower()
            if isinstance(v, dict) and ("note" in key or "hook" in v or "hook_resolution" in v or "theme_closure" in v):
                for nk, nv in v.items():
                    if nk in ("hook_resolution", "theme_closure") and isinstance(nv, str) and not note.get(nk):
                        note[nk] = nv.strip()
                continue
            if not isinstance(v, (str, int, float)) or not str(v).strip():
                continue
            if "hook" in key:
                note.setdefault("hook_resolution", "")
                if not note["hook_resolution"]:
                    note["hook_resolution"] = str(v).strip()
                continue
            if any(w in key for w in ("theme", "closure", "resolution", "type", "status", "intent", "nuance", "note")):
                note.setdefault("theme_closure", "")
                if not note["theme_closure"]:
                    note["theme_closure"] = str(v).strip()
                continue
            scene_vals.append(str(v).strip())
        plot["ending"] = " ".join(scene_vals)
        if note:
            plot["ending_note"] = {"hook_resolution": note.get("hook_resolution", ""), "theme_closure": note.get("theme_closure", "")}
        if DEBUG_MODE:
            print("[plot修復] ending が dict だったため情景を文字列に、注記を ending_note に振り分けました", file=sys.stderr)
    elif isinstance(ending, list):
        plot["ending"] = " ".join(str(v).strip() for v in ending if isinstance(v, (str, int, float)) and str(v).strip())
        if DEBUG_MODE:
            print("[plot修復] ending が list だったため文字列に変換しました", file=sys.stderr)
    if not plot.get("ending"):
        plot["ending"] = ""
        if DEBUG_MODE:
            print("[plot修復] ending が欠落していたためデフォルト補完しました", file=sys.stderr)
    # 主人公が characters に含まれていない場合は先頭に追加する（GMに渡す登場人物一覧から主人公が抜けないように）
    prot_name = plot.get("protagonist", {}).get("name", "") if isinstance(plot.get("protagonist"), dict) else ""
    if prot_name and isinstance(plot.get("characters"), list):
        if not any(isinstance(c, dict) and c.get("name") == prot_name for c in plot["characters"]):
            role = plot["protagonist"].get("goal_surface", "") or "主人公"
            plot["characters"].insert(0, {"name": prot_name, "role": role})
            if DEBUG_MODE:
                print("[plot修復] 主人公が characters に無かったため追加しました", file=sys.stderr)
    if not isinstance(plot.get("ending_note"), dict) or not plot["ending_note"]:
        plot["ending_note"] = {"hook_resolution": "", "theme_closure": ""}
        if DEBUG_MODE:
            print("[plot修復] ending_note が欠落していたためデフォルト補完しました", file=sys.stderr)

    return plot
