"""出力言語の切り替え（英語版の試作）。

方針：内部のプロンプト・注入文は日本語のまま。出力の言語と長さに関わる語句だけを、
API に渡す直前に差し替える（プロンプト全文の英訳はしない）。
"""

LANG = "ja"  # "ja" / "en"。起動オプション --lang en で切り替える

# 英語のとき、API に渡す直前に差し替える語句（完全一致）
_EN_REPLACE = [
    ("日本語で応答すること。日本語以外の混入禁止",
     "英語（English）で応答すること。地の文・セリフ・人物名を含め、日本語を混ぜないこと。主人公は二人称（you）で書く"),
    ("300字以内", "150語（words）以内"),
    ("500字以内", "250語（words）以内"),
    ("200字程度", "100語（words）程度"),
    ("短い日本語タイトル", "短い英語（English）のタイトル"),
]

# 英語のときだけプロット生成の依頼に足す1行（人物名・文化圏）
EN_PLOT_LINE = (
    "人物名・地名・舞台の文化圏は、ジャンルやタイトルに指定がなければ英語圏のものにする。"
    "指定があればそれに従う。いずれの場合も人物名・行事・習慣・制度を一つの文化圏で一貫させる。"
    "プロットの各項目は日本語で書いてよいが、人物名・地名などの固有名詞は英語表記にする。"
    "timing の値は「序盤」「中盤」「クライマックス直前」「クライマックス」のまま変えない。"
)

# 英語のときだけ自動プレイのプレイヤーに足す1行
EN_PLAYER_LINE = "行動は英語（English）で、主語を省いた命令形で書くこと（例：Walk to the door.）。"

# 英語のときだけバッチのジャンル・タイトル生成に足す1行
EN_GENRE_TITLE_LINE = "ジャンル名・タイトルは英語（English）で書くこと。"


def is_en() -> bool:
    return LANG == "en"


def localize_text(text: str) -> str:
    if not is_en() or not isinstance(text, str):
        return text
    for a, b in _EN_REPLACE:
        text = text.replace(a, b)
    return text


def localize(messages: list) -> list:
    """API に渡すメッセージの写しを返す（履歴そのものは書き換えない）。"""
    if not is_en():
        return messages
    return [{**m, "content": localize_text(m.get("content", ""))} for m in messages]
