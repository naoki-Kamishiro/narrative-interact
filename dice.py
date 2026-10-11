"""
ダイス判定モジュール。
行動がダイス判定を必要とするかをLLMに問い合わせ、
必要なら1d20を振って結果を返す。

難易度はLLMに直接数値を出させず、risk/uncertaintyの2軸を
low/mid/highで分類させ、Python側で決定論的に難易度へ変換する。
これにより、行動説明文の長さや複雑さに難易度が引きずられることを防ぐ。
"""

import json
import random
import re
from api import chat_json

JUDGE_PROMPT = """\
プレイヤーの行動を受け取り、ダイス判定が必要かどうかを判断してください。

以下のいずれかに該当する場合のみ判定が必要：
・成否が物語を分岐させる行動
・能力・技術・運・交渉・修理・調査など不確実性がある行動
・プレイヤーが重要なリスクを取る行動
・隠された情報の発見・原因究明・証拠収集など目的達成を伴う観察行動

行動の文章の長さや複雑さ・専門用語の多さで難しさを判断しないこと。
行動そのものの実質的な内容だけを見て判断すること。

以下のJSON形式のみで返答してください。それ以外の文字は含めないこと。

判定不要の場合：
{"need_roll": false}

判定必要の場合：
{"need_roll": true, "risk": "low|mid|high", "uncertainty": "low|mid|high", "reason": "判定理由を10文字以内で"}

risk: 失敗した場合の代償の重さ（low=軽い, mid=中程度, high=重大）
uncertainty: 行動の結果がどれだけ読みにくいか（low=ほぼ確実, mid=半々, high=非常に不確実）
"""

# risk/uncertaintyの組み合わせから難易度を決定論的に算出するテーブル
_LEVEL_VALUE = {"low": -2, "mid": 0, "high": 2}
_BASE_DIFFICULTY = 9  # d20で約60%の成功率を基準にする

# 難易度プリセット（起動時のプレイヤー選択でオフセットを加える）
DIFFICULTY_PRESETS = {
    "easy": -2,
    "normal": 0,
    "hard": 2,
}
_difficulty_offset = 0  # main.pyから設定される

def set_difficulty_preset(preset: str) -> None:
    """起動時に難易度プリセットを設定する。"""
    global _difficulty_offset
    _difficulty_offset = DIFFICULTY_PRESETS.get(preset, 0)

def roll_d20() -> int:
    return random.randint(1, 20)

def _determine_intensity(dice: int, difficulty: int) -> str:
    """出目と難易度のマージンから結果の強度を判定する。"""
    margin = dice - difficulty
    if margin >= 8:
        return "decisive"
    elif margin >= -3:
        return "normal"
    else:
        return "severe"

def _compute_difficulty(risk: str, uncertainty: str) -> int:
    """risk/uncertaintyの2軸から難易度をローカルで決定論的に計算する。"""
    risk_v = _LEVEL_VALUE.get(risk, 0)
    unc_v = _LEVEL_VALUE.get(uncertainty, 0)
    difficulty = _BASE_DIFFICULTY + risk_v + unc_v + _difficulty_offset
    return max(6, min(18, difficulty))

def judge(action: str, history: list) -> dict | None:
    # 直近のGM応答を文脈として渡す（状況依存の判定精度向上のため）
    last_gm = next(
        (m["content"] for m in reversed(history) if m["role"] == "assistant"),
        None
    )
    context_line = f"\n現在の状況（直前のGM描写）:\n{last_gm[:300]}\n\n" if last_gm else ""
    messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": f"{context_line}行動: {action}"},
    ]
    raw = chat_json(messages)

    try:
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()
        cleaned = re.sub(r"```", "", cleaned).strip()
        data = json.loads(cleaned)
    except (json.JSONDecodeError, Exception):
        return None

    if not data.get("need_roll", False):
        return None

    risk = data.get("risk", "mid")
    uncertainty = data.get("uncertainty", "mid")
    reason = data.get("reason", "判定")

    difficulty = _compute_difficulty(risk, uncertainty)
    dice = roll_d20()
    success = dice >= difficulty
    intensity = _determine_intensity(dice, difficulty)

    return {
        "dice": dice,
        "difficulty": difficulty,
        "reason": reason,
        "success": success,
        "intensity": intensity,
    }

def display_result(result: dict) -> None:
    """ダイス結果をコンソールに表示する。"""
    outcome = "成功" if result["success"] else "失敗"
    intensity_label = {
        "decisive": "（決定的）",
        "normal": "",
        "severe": "（重大）",
    }.get(result.get("intensity", "normal"), "")
    print(f"🎲 判定: {result['reason']} / 難易度{result['difficulty']} / 出目{result['dice']} → {outcome}{intensity_label}")

def build_user_tag(action: str, result: dict) -> str:
    """GMへuserメッセージとして渡す判定結果タグを生成する。"""
    outcome = "成功" if result["success"] else "失敗"
    intensity = result.get("intensity", "normal")

    if result["success"] and intensity == "decisive":
        instruction = (
            "決定的な成功として描写すること。"
            "戦闘・物理的な対立の決着に該当する場合は、事態を大きく動かす一撃・転換点として描写してよい。"
            "情報収集・調査・交渉・解析に該当する場合は、新しい事実・重要な手がかり・状況の大きな変化を描写すること。"
            "ただしその情報からプレイヤー自身が次の行動を考えられる余地を残すこと。最終攻略法・解決手順は一段階隠し、示唆に留めること。"
            "黒幕・世界の真相・最終目的・正解ルートの確定も描写してはならない。"
            "成功で得られる情報量は行動内容とプレイヤーキャラクターの能力・知識の範囲を超えないこと。"
            "複数の目的・行動が含まれる場合、1回の判定では最も重要な目的のみを判定する。成功時はその目的に対応する結果のみを描写し、副次的な行動から重要な結果を追加で得てはならない。"
            "この行動がプロットの目標を直接・完全に達成した場合のみ、この結果をもって物語をエンディングに導いてよい。"
            "交渉・約束・準備・開始・合意は目標の達成ではないため、エンディングの条件を満たさない。"
        )
    elif result["success"]:
        instruction = (
            "成功として状況が一歩前進したとして描写すること。"
            "部分的な手がかり・小さな前進・相手の態度が軟化する程度に留めること。"
            "物語の核心・黒幕・最終目的・重要な秘密は複数の段階を経て明らかにすること。判定結果から導かれる推論は確認された事実と区別し、未確認の動機・目的・真相を確定してはならない。"
            "成功で得られる情報量は行動内容とプレイヤーキャラクターの能力・知識の範囲を超えないこと。"
            "複数の目的・行動が含まれる場合、1回の判定では最も重要な目的のみを判定する。成功時はその目的に対応する結果のみを描写し、副次的な行動から重要な結果を追加で得てはならない。"
            "この行動がプロットの目標を直接・完全に達成した場合のみ、この結果をもって物語をエンディングに導いてよい。"
            "交渉・約束・準備・開始・合意は目標の達成ではないため、エンディングの条件を満たさない。"
        )
    elif intensity == "severe":
        instruction = (
            "目的は達成できない。代わりに次の行動で対処可能な、小規模な制約・障害を最大1つ発生させる。"
            "障害は行動対象に直接関連する失敗結果として描写し、既存の状況変化・時間経過・相手の反応による影響のみ許可する。"
            "失敗を補うためだけに、プロットで設定されていない新規の人物・事件・証拠・偶然の出来事を追加してはならない。"
            "物語の進行可能性を損なう不可逆的な状態変化は、事前に設定されたプロット上の必然性がある場合を除き発生させない。"
            "失敗によってプレイヤーが調査・行動していた対象そのものを変質・破壊してはならない。失敗前に存在していた物の性質・形状・アクセス可能性を失敗後に変えてはならない。"
        )
    else:
        instruction = (
            "失敗の場合は行動が不成立に終わったとして描写すること。"
            "誰も気づかず何も変化しないこともあり、その場合は絶対に不穏な空気や緊張を作り出さないこと。"
            "言葉による行動（侮辱・告白・説得など）が失敗した場合は、"
            "言葉が効果的に響かなかったとして描写すること。"
            "失敗した事実を明確にした上で、次に取りうる行動の余地（別の手がかり・追加条件・障害など）を自然に示すこと。"
            "失敗を成功に近い描写にしてはならない。"
        )
    return (
        f"{action}\n"
        f"（判定結果: {result['reason']} / 難易度{result['difficulty']} / 出目{result['dice']} → {outcome}。"
        f"{instruction}"
        f"判定結果を受けてから、その結果に整合する物語を構築すること。先に結末を決めて判定へ合わせてはならない。"
        f"判定結果はシーンの方向性を決定する。物語はその結果を自然な因果関係で表現すること。"
        f"判定は物語を制限するものではなく、物語上の事実を確定するものである。成功・失敗を問わず、描写は判定結果と矛盾してはならない。"
        f"判定結果を地の文に出力しないこと。）"
    )
