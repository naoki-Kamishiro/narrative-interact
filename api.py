from openai import OpenAI
import threading
import time
from config import LM_STUDIO_URL, API_KEY, MAX_TOKENS, TEMPERATURE

_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LM_STUDIO_URL, api_key=API_KEY)
    return _client

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
            max_tokens=2048,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR: {e}]"
    finally:
        stop_event.set()
        t.join()
