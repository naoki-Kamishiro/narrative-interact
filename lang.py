"""出力言語の切り替え（英語版の試作）。

方針：内部のプロンプト・注入文は日本語のまま。出力の言語と長さに関わる語句だけを、
API に渡す直前に差し替える（プロンプト全文の英訳はしない）。
"""

LANG = "ja"  # "ja" / "en"。起動オプション --lang en で切り替える

# 英語のとき、API に渡す直前に差し替える語句（完全一致）
_EN_REPLACE = [
    ("日本語で応答すること。日本語以外の混入禁止",
     "英語（English）で応答すること。地の文・セリフ・人物名を含め、日本語を混ぜないこと。主人公は二人称（you）で書く。Markdown（太字・見出し・箇条書き・番号付きの列挙）は使わない"),
    ("300字以内", "150語（words）以内"),
    ("500字以内", "250語（words）以内"),
    ("200字程度", "100語（words）程度"),
    ("短い日本語タイトル", "短い英語（English）のタイトル"),
    ("判定理由を10文字以内で", "判定理由を英語（English）で5語以内で"),
    ("20字以内の一言のみ", "英語（English）で10語以内の一言のみ"),
    ("行動を10〜20字で簡潔に記述する", "行動を英語（English）で5〜10語で簡潔に記述する"),
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


# ビートのタイミング（内部の値は日本語のまま）の表示用の英語名
TIMING_EN = {"序盤": "early", "中盤": "middle", "終盤": "late", "クライマックス直前": "before climax", "クライマックス": "climax", "エンディング": "ending"}


def timing_label(t: str) -> str:
    """デバッグ表示などでタイミングを出すとき用。英語なら英語名に訳す。"""
    return TIMING_EN.get(t, t) if is_en() else t


def is_en() -> bool:
    return LANG == "en"


def t(ja: str, en: str) -> str:
    """画面表示用。日本語と英語を並べて書き、今の言語の方を返す。"""
    return en if is_en() else ja


def ask_language() -> None:
    """起動直後に表示言語を選ぶ（日英併記）。"""
    global LANG
    print()
    print("Language / 言語:")
    print("  1. 日本語")
    print("  2. English")
    while True:
        c = input("[1/2]: ").strip()
        if c in ("1", "2"):
            LANG = "ja" if c == "1" else "en"
            return
        print("1 か 2 を入力してください。 / Please enter 1 or 2.")


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
