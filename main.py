"""
ナラティブインタラクト（LM Studio版）
ジャンルとタイトルを入力するだけで物語が始まる。
"""

import sys
import state
import history as hist
import plot as plot_mod
import save as save_mod
from api import chat
from display import gm_print, system_print, error_print, hr
from prompt import build_start_message
import dice as dice_mod
import beat as beat_mod

COMMANDS = {
    "/save": "セーブ",
    "/load": "ロード",
    "/quit": "セーブせずに終了",
    "/next": "不介入で物語を進める",
    "/n":    "不介入で物語を進める",
    "/hint": "行動候補を3〜4つ表示",
    "/retry": "直前のGM応答を再生成",
    "/r":    "直前のGM応答を再生成",
    "/help": "コマンド一覧",
    "/h":    "コマンド一覧",
}

ENDING_MARKER = "【エンディング】"

def show_help():
    hr()
    for cmd, desc in COMMANDS.items():
        print(f"  {cmd:<8} {desc}")
    hr()

def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        print("\n終了します。")
        sys.exit(0)
    except KeyboardInterrupt:
        print()
        return ""

def call_gm(messages: list, max_retries: int = 1) -> str:
    reply = chat(messages)
    attempt = 0
    while reply.startswith("[ERROR") and attempt < max_retries:
        system_print("応答生成に失敗したため再試行します...")
        reply = chat(messages)
        attempt += 1
    if not reply.startswith("[ERROR"):
        reply = beat_mod.filter_output(reply)
        if ENDING_MARKER in reply:
            reply = reply.replace(ENDING_MARKER, "").strip()
            reply = reply + "\n" + ENDING_MARKER
        gm_print(reply)
    return reply


def _is_strong() -> bool:
    return state.get_plot_mode() == "strong"


def _build_api_messages(h: list) -> list:
    """strongモードならビート注入版、それ以外は通常版でAPI用メッセージを返す。"""
    if _is_strong():
        s = state.get()
        queue = s.get("beat_queue", [])
        ptr = s.get("beat_ptr", 0)
        msgs, debug = hist.build_for_api_with_beat(h, queue, ptr)
        if debug:
            print(debug, file=sys.stderr)
        return msgs
    return hist.build_for_api(h)


def _after_reply(reply: str) -> None:
    """strongモード: GM応答後にビートポインタを進める。"""
    if not _is_strong():
        return
    s = state.get()
    queue = s.get("beat_queue", [])
    ptr = s.get("beat_ptr", 0)
    queue, ptr = beat_mod.advance(queue, ptr, reply)
    state.update({"beat_queue": queue, "beat_ptr": ptr})

def check_ending(reply: str) -> bool:
    return ENDING_MARKER in reply

PLOT_MODE_LABELS = {
    "1": ("off", "プロット参照・自由"),
    "2": ("on", "プロット参照・緩拘束"),
    "3": ("strong", "プロット参照・強拘束"),
    "4": ("improv", "プロットなし・即興"),
}

def ask_plot_mode() -> str:
    print()
    print("物語の軸:")
    print("  1. プロット参照・自由")
    print("  2. プロット参照・緩拘束（おすすめ）")
    print("  3. プロット参照・強拘束")
    print("  4. プロットなし・即興")
    while True:
        choice = ask("選択 [1/2/3/4]: ")
        if choice in PLOT_MODE_LABELS:
            mode, label = PLOT_MODE_LABELS[choice]
            system_print(f"物語の軸: {label}")
            return mode
        system_print("1〜4のいずれかを入力してください。")

def ask_use_dice() -> bool:
    print()
    ans = ask("ダイス判定を使いますか？ [Y/n]: ")
    use_dice = ans.lower() != "n"
    system_print(f"ダイス判定: {'使う' if use_dice else '使わない'}")
    return use_dice

DIFFICULTY_LABELS = {
    "1": ("easy", "易しい"),
    "2": ("normal", "標準"),
    "3": ("hard", "厳しい"),
}

def ask_difficulty() -> str:
    print()
    print("難易度:")
    print("  1. 易しい")
    print("  2. 標準（おすすめ）")
    print("  3. 厳しい")
    while True:
        choice = ask("選択 [1/2/3]: ")
        if choice in DIFFICULTY_LABELS:
            preset, label = DIFFICULTY_LABELS[choice]
            system_print(f"難易度: {label}")
            return preset
        system_print("1〜3のいずれかを入力してください。")

def start_new_game() -> tuple[list, str, str]:
    genre = ask("ジャンル: ")
    title = ask("タイトル: ")
    plot_mode = ask_plot_mode()
    use_dice = ask_use_dice()
    if use_dice:
        difficulty_preset = ask_difficulty()
        dice_mod.set_difficulty_preset(difficulty_preset)
    else:
        difficulty_preset = "normal"

    if plot_mode == "improv":
        system_print("プロット生成なし")
        plot = {}
    else:
        plot = plot_mod.generate(genre, title)

    state.init(genre, title, plot, plot_mode)
    state.update({"use_dice": use_dice, "difficulty_preset": difficulty_preset})

    if plot_mode == "strong" and plot:
        queue = beat_mod.build_queue(plot)
        state.update({"beat_queue": queue, "beat_ptr": 0, "ending_suppressed": False})
        print(f"[BEAT] queue built: {len(queue)} beats", file=sys.stderr)

    h = hist.new_history(plot, plot_mode, genre)
    start_msg = build_start_message(genre, title, plot)
    h = hist.add_user(h, start_msg)

    print()
    print(f"── 「{title}」 開始 ──")
    system_print("行き詰まったら /hint で行動候補を表示できます。")
    print()

    reply = call_gm(_build_api_messages(h))
    if reply.startswith("[ERROR"):
        error_print("応答生成に失敗しました。/retryで再試行できます。")
    else:
        h = hist.add_assistant(h, reply)
        _after_reply(reply)

    return h, genre, title

def _print_history(h: list) -> None:
    """履歴を順番に表示する。systemメッセージとダイス結果タグは除外。"""
    for m in h:
        if m["role"] == "system":
            continue
        content = m["content"]
        if m["role"] == "assistant":
            gm_print(content)
        elif m["role"] == "user":
            # ダイス結果タグ（判定結果: ...）を除いてプレイヤー行動のみ表示
            # タグ付きの場合、最初の行がプレイヤー入力
            action_line = content.split("\n")[0]
            # （ ...） で始まるシステム挿入メッセージは表示しない
            if not action_line.startswith("（"):
                print(f"\nあなたの行動: {action_line}")

def resume_game() -> tuple[list, str, str] | None:
    s, h = save_mod.load()
    if not s or not h:
        system_print("セーブデータが見つかりません。")
        return None
    state.load_from(s)
    plot = s.get("plot", {})
    plot_mode = s.get("plot_mode", "off")
    dice_mod.set_difficulty_preset(s.get("difficulty_preset", "normal"))

    # 旧セーブにbeat_queueがない場合は再構築
    if plot_mode == "strong" and plot and not s.get("beat_queue"):
        queue = beat_mod.build_queue(plot)
        state.update({"beat_queue": queue, "beat_ptr": 0, "ending_suppressed": False})
        print(f"[BEAT] queue rebuilt on load: {len(queue)} beats", file=sys.stderr)
    title = s.get("title", "")
    genre = s.get("genre", "")
    h = hist.rebuild_system(h, plot, plot_mode, genre)
    system_print(f"ロード完了: 「{title}」　履歴を表示します...")
    print()

    _print_history(h)

    return h, genre, title

def handle_ending(h: list) -> tuple[list, bool]:
    """エンディング後の3択を処理する。戻り値は (履歴, 終了するか)。"""
    system_print("エンディングを迎えました。お疲れさまでした。")
    print("  1. 終了する")
    print("  2. エピローグを生成する")
    print("  3. 物語を続行する")
    while True:
        ans = ask("選択 [1/2/3]: ")
        if ans == "1":
            return h, True
        if ans == "2":
            h = hist.add_user(h, "この物語のエピローグを200字程度で書いてください。意味・テーマ・主人公の変化の総括や説明はせず、主人公・世界・人物関係の具体的な状態の変化だけを描写して、余韻を残してください。")
            reply = call_gm(hist.build_for_api(h))
            if reply.startswith("[ERROR"):
                error_print("エピローグの生成に失敗しました。")
                h.pop()
            else:
                h = hist.add_assistant(h, reply)
            return h, True
        if ans == "3":
            # 続行通知はuserとして追加する。次のプレイヤー入力とは
            # build_for_api() で連結されるので、入力は失われない。
            h = hist.add_user(h, "（プレイヤーが続行を選択しました。物語はまだ終わっていません。引き続き状況を描写してください。）")
            return h, False
        system_print("1か2か3を入力してください。")

def push_user(h: list, content: str, replace_pending: bool) -> list:
    """userメッセージを追加する。replace_pending=Trueなら、エラーで未応答のまま
    残っている直前のuserメッセージを置き換える（放棄された行動として扱う）。"""
    if replace_pending and h and h[-1]["role"] == "user":
        h.pop()
    return hist.add_user(h, content)

def main():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║  ナラティブインタラクト (LM Studio版)    ║")
    print("╚══════════════════════════════════════════╝")
    print()
    print("コマンド一覧は /help または /h")
    print()

    h, genre, title = None, "", ""

    if save_mod.exists():
        s, _ = save_mod.load()
        saved_title = s.get("title", "") if s else ""
        system_print(f"セーブデータが見つかりました:「{saved_title}」")
        print("  1. 続きから始める")
        print("  2. 削除して新しく始める")
        while True:
            ans = ask("選択 [1/2]: ")
            if ans == "1":
                result = resume_game()
                if result:
                    h, genre, title = result
                break
            elif ans == "2":
                save_mod.delete()
                system_print("セーブデータを削除しました。")
                break
            system_print("1か2を入力してください。")

    if h is None:
        h, genre, title = start_new_game()

    # 直前の生成がエラーで、userメッセージが未応答のまま履歴に残っているか
    pending_failed = False

    while True:
        action = ask("\nあなたの行動: ")

        if not action:
            continue

        if action in ("/help", "/h"):
            show_help()
            continue

        if action == "/quit":
            print("終了します。")
            break

        if action == "/save":
            save_mod.save(state.get(), h)
            continue

        if action == "/load":
            result = resume_game()
            if result:
                h, genre, title = result
                pending_failed = False
            continue

        if action in ("/retry", "/r"):
            # 直前がassistantなら削除して再生成。直前がuser（エラーで未応答）なら
            # そのuserメッセージ（ダイス結果込み）をそのまま再利用する。
            if h and h[-1]["role"] == "assistant":
                h.pop()
            reply = call_gm(_build_api_messages(h))
            if reply.startswith("[ERROR"):
                error_print("応答生成に失敗しました。/retryで再試行できます。")
                pending_failed = True
                continue
            pending_failed = False
            h = hist.add_assistant(h, reply)
            _after_reply(reply)
            if check_ending(reply):
                h, quit_ = handle_ending(h)
                if quit_:
                    break
            continue

        if action.startswith("/") and action not in COMMANDS:
            system_print(f"コマンドにありません: {action}　/help で一覧を確認できます。")
            continue

        if action in ("/next", "/n"):
            h = push_user(h, "（プレイヤーは静かに見守っている。物語を自然に進めてください。）", pending_failed)
            reply = call_gm(_build_api_messages(h))
            if reply.startswith("[ERROR"):
                error_print("応答生成に失敗しました。/retryで再試行できます。")
                pending_failed = True
                continue
            pending_failed = False
            h = hist.add_assistant(h, reply)
            _after_reply(reply)
            if check_ending(reply):
                h, quit_ = handle_ending(h)
                if quit_:
                    break
            continue

        if action == "/hint":
            hint_msg = hist.build_for_api(h) + [{
                "role": "user",
                "content": "今の状況でプレイヤーが取れる行動を3〜4つ、短く箇条書きで提案してください。"
            }]
            call_gm(hint_msg)
            continue

        # ダイス判定（use_diceがTrueの場合のみ）
        dice_result = dice_mod.judge(action, h) if state.get().get("use_dice", True) else None
        if dice_result:
            dice_mod.display_result(dice_result)
            user_msg = dice_mod.build_user_tag(action, dice_result)
        else:
            user_msg = action
        h = push_user(h, user_msg, pending_failed)

        reply = call_gm(_build_api_messages(h))

        if reply.startswith("[ERROR"):
            error_print("応答生成に失敗しました。/retryで再試行できます。")
            # userメッセージ（ダイス結果込み）は保持したまま続行。
            # /retryで再利用でき、別の行動を入力した場合は置き換えられる。
            pending_failed = True
            continue

        pending_failed = False
        h = hist.add_assistant(h, reply)
        _after_reply(reply)

        if check_ending(reply):
            # strongモードのエンディング早出し抑止
            if _is_strong() and not state.get().get("ending_suppressed", False):
                s = state.get()
                queue = s.get("beat_queue", [])
                ptr = s.get("beat_ptr", 0)
                queue, ptr, suppressed = beat_mod.handle_ending_suppression(queue, ptr)
                if suppressed:
                    state.update({"beat_queue": queue, "beat_ptr": ptr, "ending_suppressed": True})
                    # エンディングマーカーを除いて続行
                    h[-1] = {"role": "assistant", "content": h[-1]["content"].replace(ENDING_MARKER, "").strip()}
                    continue

            h, quit_ = handle_ending(h)
            if quit_:
                break

if __name__ == "__main__":
    main()
