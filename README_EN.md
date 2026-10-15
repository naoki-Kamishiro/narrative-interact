# Narrative Interact

An interactive fiction system that runs on a local LLM via LM Studio.

You specify a genre and a title — the AI generates the plot, and you play through it by typing actions in natural language.

---

## What it does

When you start a session, the system automatically generates a plot: protagonist, characters, conflicts, twists, key choices, and an ending. The GM (Game Master) knows this plot but never reveals it directly.

You move the story forward by typing actions — one at a time, in plain text.

```
> Step forward.
> Look the elf in the eye.
> Reach out toward the membrane of light.
```

Each action is evaluated for uncertainty and risk. If a dice roll is needed, a d20 is thrown. The GM then narrates the outcome — success or failure — and the story branches accordingly.

The story ends when the plot reaches its conclusion. The GM decides when that is.

---

## Features

- **Auto plot generation** — Genre and title are the only inputs needed. The system generates the full narrative structure before play begins.
- **Dice resolution** — Actions are automatically judged for whether a roll is needed. Difficulty is computed locally from two axes (risk × uncertainty), not by the LLM.
- **Beat injection (strong mode)** — Plot beats (twists, failures, character appearances, key choices) are silently injected into GM instructions at the right timing. The player never sees them.
- **Ending detection** — The GM outputs `【エンディング】` when the story concludes. An epilogue is then generated automatically.
- **Save / Load** — Sessions are saved as JSON. You can resume any session later.
- **Auto-play mode** — The system can play itself, useful for testing and evaluation.

---

## Requirements

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) running a local LLM on `localhost:1234`
- A model capable of following complex Japanese instruction prompts

> **Note:** The GM system prompt is written in Japanese. The model needs to handle Japanese instructions reliably. Models in the 7B–14B range vary significantly in quality for this task.

---

## Setup

```bash
git clone https://github.com/naoki-Kamishiro/narrative-interact.git
cd narrative-interact
pip install -r requirements.txt
```

Start LM Studio and load a model. Make sure the local server is running on port `1234`.

Then run:

```bash
python main.py
```

---

## Usage

On startup, you will be prompted for:

1. **Genre** — e.g. `Fantasy`, `Mystery`, `Sci-Fi`
2. **Title** — e.g. `The Elf and the Old Man`
3. **Plot mode** — `weak` (GM follows the plot loosely) or `strong` (beat injection active)
4. **Difficulty** — `easy` / `normal` / `hard`

After that, the opening scene is generated and you begin.

**In-game commands:**

| Command | Description |
|---------|-------------|
| `/save` | Save the current session |
| `/load` | Load a saved session |
| `/hint` | Show 3–4 suggested actions |
| `/retry` or `/r` | Regenerate the last GM response |
| `/help` or `/h` | Show command list |
| `/quit` | Quit without saving |

---

## How it works

### Plot generation

Before play starts, an LLM call generates a complete plot structure in JSON:

- Protagonist wound / surface goal / deep desire
- Characters and their roles
- Misconceptions the player starts with
- Failures and twists (with timing tags: early / mid / climax)
- Key choices with costs
- Climax setting and ending

This plot is passed to the GM as a hidden system prompt. The GM knows it; the player doesn't.

### Dice resolution

Every player action is sent to a separate LLM call that judges whether a roll is needed. If yes, it returns `risk` and `uncertainty` (each `low` / `mid` / `high`). Difficulty is then computed locally:

```
difficulty = base(9) + risk_value + uncertainty_value + preset_offset
```

The LLM never outputs a difficulty number directly — this prevents prompt-length bias inflating difficulty.

The actual die roll is `random.randint(1, 20)` in Python. The LLM has no influence over the result — it only classifies the action, never touches the numbers.

### Beat injection (strong mode)

In strong mode, plot beats are queued at startup. Each turn, the current beat is appended to the GM's user message as a hidden scene directive. The player sees the result in the narration; they never see the directive itself.

Character beats are confirmed by checking whether the character's name appears in the GM's response. Other beat types are trusted after one injection and the pointer advances.

---

## Project structure

```
main.py       — Main loop, input handling, command dispatch
plot.py       — Plot generation via LLM
prompt.py     — System prompt builder
api.py        — LM Studio API wrapper
dice.py       — Dice roll and difficulty logic
beat.py       — Beat queue and injection (strong mode)
history.py    — Conversation history management
state.py      — Session state management
save.py       — Save / load logic
display.py    — Colored console output
```

---

## License

MIT

---

## Known issues

- **Auto-play action loops**: The player LLM may repeat actions on the same target by slightly varying the verb (e.g. "grip" → "grip tightly" → "apply force"). A rule requiring the player to switch targets or locations after 3 consecutive actions on the same object has been added to reduce this. Complete suppression depends on the model.
- **Player LLM inner-state output**: In auto-play mode, the player LLM may output internal actions such as "steel myself" or "accept the situation". A rule requiring all actions to be externally observable (physical, verbal, or movement) has been added to the player prompt.

---

## Notes

This project is under active development. The GM prompt is currently Japanese-only. English output mode and an English prompt variant are planned.

Feedback and pull requests are welcome.
