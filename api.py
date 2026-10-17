from openai import OpenAI
import threading
import time
from config import LM_STUDIO_URL, API_KEY, MAX_TOKENS, TEMPERATURE

PLAYER_URL = LM_STUDIO_URL  # GMと同じポートを使用（同一モデルでGM・プレイヤー兼用）

_client: OpenAI | None = None
_player_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LM_STUDIO_URL, api_key=API_KEY)
    return _client

def get_player_client() -> OpenAI:
    global _player_client
    if _player_client is None:
        _player_client = OpenAI(base_url=PLAYER_URL, api_key=API_KEY)
    return _player_client

def _show_progress(stop_event: threading.Event) -> None:
    """生成中にドットを表示するスレッド関数。"""
    import sys
    chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r生成中 {chars[i % len(chars)]}")
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 20 + "\r")
    sys.stdout.flush()

def chat(messages: list) -> str:
    stop_event = threading.Event()
    t = threading.Thread(target=_show_progress, args=(stop_event,), daemon=True)
    t.start()
    try:
        client = get_client()
        response = client.chat.completions.create(
            model="local",
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR: {e}]"
    finally:
        stop_event.set()
        t.join()

def chat_player(gm_response: str, system_prompt: str, recent_actions: list | None = None) -> str:
    """プレイヤーLLMにGM応答を渡して行動を生成する（自動プレイ用）。
    recent_actions: 直近のプレイヤー行動リスト（ループ抑止用）。"""
    user_content = gm_response
    if recent_actions:
        actions_text = "\n".join(f"  - {a}" for a in recent_actions)
        user_content = (
            f"【直近の自分の行動（繰り返し禁止の参考に）】\n{actions_text}\n\n"
            f"【現在の状況】\n{gm_response}"
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ]
    try:
        client = get_player_client()
        response = client.chat.completions.create(
            model="local",
            messages=messages,
            max_tokens=200,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR: {e}]"


def chat_json(messages: list) -> str:
    """JSON出力専用。プロット生成など内部処理用。"""
    stop_event = threading.Event()
    t = threading.Thread(target=_show_progress, args=(stop_event,), daemon=True)
    t.start()
    try:
        client = get_client()
        response = client.chat.completions.create(
            model="local",
            messages=messages,
            max_tokens=4096,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR: {e}]"
    finally:
        stop_event.set()
        t.join()
