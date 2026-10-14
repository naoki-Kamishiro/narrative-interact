# Narrative Interact

LM Studio用インタラクティブフィクションシステム。  
ジャンルとタイトルを入力するだけでGM（LLM）が物語を生成し、プレイヤーが行動を入力して物語を進める。

## 動作環境

- Python 3.10以上
- [LM Studio](https://lmstudio.ai/) （ローカルサーバーとして起動）
- 推奨モデル：Gemma4 12B

## セットアップ

```bash
git clone https://github.com/naoki-Kamishiro/narrative-interact.git
cd narrative-interact
```

`config.py` でLM StudioのエンドポイントとモデルIDを設定する。

```python
# config.py
LM_STUDIO_URL = "http://localhost:1234/v1"
MODEL_ID = "your-model-id"
```

## 使い方

```bash
# 手動プレイ
python main.py

# 自動プレイ（プレイヤーもLLMが担当）
python main.py --auto normal    # 通常モード
python main.py --auto deviate   # 逸脱モード（GM制約を意図的に超える行動）

# デバッグ出力あり
python main.py --auto normal --debug
```

起動後、ジャンルとタイトルを入力するとGMが物語を始める。

### コマンド一覧

| コマンド | 機能 |
|---------|------|
| `/save` | セーブ |
| `/load` | ロード |
| `/quit` | セーブせずに終了 |
| `/hint` | 行動候補を3〜4つ表示 |
| `/retry` または `/r` | 直前のGM応答を再生成 |
| `/help` または `/h` | コマンド一覧 |

## ライセンス

MIT
