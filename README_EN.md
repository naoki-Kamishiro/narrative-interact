# Narrative Interact

> ⚠️ This project is under development. Unexpected behavior or bugs may occur.

> **Language note:** The system currently runs in Japanese only. The UI, the prompts, and the GM's narration are all in Japanese. An English version may be provided in the future.

[日本語版 README はこちら](README.md)

An interactive fiction system that runs on a local LLM.
Enter a genre and a title, and the LLM acts as the GM (game master) and generates a story automatically. You play the protagonist and type any action you like; the GM advances the story based on the result.

Instead of reading a pre-written scenario, you step into a story the LLM generates and change how it unfolds through your own actions. Because you can choose how tightly the story is bound to its plot, you can try anything from following the story's flow to actively steering it somewhere else.

## Background

I first learned about local LLMs when I built an AI VTuber with Ollama. Later I found LM Studio and got hooked on having it write novels through prompt engineering.

One day I tried a pseudo-TRPG with an LLM in LM Studio using just one line: "You are the GM of a TRPG." It was far more fun than I expected. The motivation of "I want to build something more playable on LM Studio" is where this system started.

Related articles (Japanese):
- [Chapter 4: Easy novel writing with LM Studio alone](https://note.com/kamishiro_naoki/n/n7bb219be4c1a)
- [Chapter 5: Easy TRPG with LM Studio alone?](https://note.com/kamishiro_naoki/n/n6d907b73cc56)
- [Just specify a genre and a title: I built a system for playing inside AI-generated stories](https://note.com/kamishiro_naoki/n/n374f0b0b0a0b) (introduction article for this project)

---

## Features

- **Fully local**: Uses a local LLM through LM Studio. No external API required
- **Any genre, any title**: Slice of life, mystery, fantasy, horror — anything goes
- **Automatic plot generation**: At game start, the LLM designs the story's skeleton (characters, conflicts, twists, ending)
- **Dice resolution**: Dice decide whether actions succeed. Success or failure is reflected in the GM's narration
- **Save / load**: Save mid-game and resume later
- **Choose the story's axis**: Pick from 4 levels of plot binding
- **GM one-liner**: At turning points, the GM may make a cynical one-line comment. Can be turned on or off
- **Turning-point narration boost**: At turning points, the GM is automatically prompted for more detailed narration (the per-turn guideline of 300 characters is raised to 500 or fewer). The GM's narration on turning-point turns is shown in bright yellow (applies regardless of the GM one-liner setting)

## How to play

### 1. Launch and game setup

```bash
python main.py
```

After launch, enter the following in order (prompts are in Japanese).

```
ジャンル (Genre): ミステリー
タイトル (Title): 消えた遺言状
```

Next, choose the story's axis (物語の軸).

| Choice | Mode | Description |
|------|--------|------|
| 1 | Plot reference · strict (プロット参照・強拘束) | Twists, choices, and failures are resolved as the plot dictates. The player's freedom of action is preserved while nearly all major plot elements are resolved. **Recommended for first-time play** |
| 2 | Plot reference · adaptive (プロット参照・適応) | Follows the plot but allows deviation. If the deviation becomes large, the story is reconstructed from the current situation and guided to a landing. |
| 3 | Plot reference · free (プロット参照・自由) | The plot is reference only. Deviation is fine. Suited for putting the player's free actions first. |
| 4 | No plot · improv (プロットなし・即興) | No plot is generated; the GM improvises the story. No constraints on where the story goes. |

Next, choose whether to use dice resolution (Y/n). If you use it, also choose the difficulty (easy / normal / hard).

Finally, choose whether the GM one-liner is on or off.

| Choice | Behavior |
|------|------|
| On (cynical) | At turning points, the GM makes a cynical one-line comment, such as "Well, that's one way to do it" or "...I see." |
| Off | The GM proceeds silently (the original behavior) |

**About the differences between modes**

Each mode differs in how strongly the plot constrains the GM. The same player actions can lead to very different endings depending on the mode. This difference is intentional by design.

- **Strict**: The system injects a beat (a story milestone) into the GM every turn and forces the plot to be resolved
- **Adaptive**: Deviation is checked every turn. After a cumulative 3 deviation judgments, an instruction encouraging convergence is injected; after a cumulative 5, the LLM regenerates a new plot and beat control guides the story to a landing (the count is not reset by turns without deviation)
- **Free**: The plot is only passed to the GM as reference in the system prompt; no beats are injected. Deviation is never forced back
- **Improv**: No plot generation and no beat injection; the story advances on the GM's output alone

In free, improv, and adaptive (before regeneration), an instruction to bring the story to a close is injected into the GM once the story exceeds 25 turns.

**About the GM one-liner**

The GM one-liner runs as a separate call, independent of story generation. It has no effect on the story's rules, mode, or beat progression.

The GM comments only at turning points (plot milestones, or turns the LLM judges to be turning points). Because it does not appear every turn, it carries meaning when it does. Depending on the genre and how the story develops, there may be few turning points and the one-liner may rarely appear.

In the console, `GM:` is shown in blue and the comment text in cyan, for example `GM: まあ、そういう手もあるか`.

### 2. Entering actions

Read the GM's narration and type an action as the protagonist.

```
> 机の引き出しを開ける (Open the desk drawer)
> 老人に話しかける (Talk to the old man)
> 窓から外を見る (Look out the window)
```

Actions are free-form. The GM does not reject the player's actions; it changes the world as a result of them.

### 3. Dice resolution

If dice resolution is enabled, some actions trigger a dice roll, and the outcome is reflected in the GM's narration. The difficulty can be chosen at launch (easy / normal / hard).

The roll is decided by Python's `random.randint(1, 20)`. The AI only decides "whether a roll is needed" and "how to classify the action's risk and uncertainty"; it has no involvement in the roll or the difficulty numbers.

### 4. Ending

When the story's main conflict is resolved, the GM narrates the ending and the story ends.

---

## In-game commands

| Command | Function |
|---------|------|
| `/hint` | Show 3–4 suggested actions |
| `/save` | Save |
| `/load` | Load |
| `/retry` or `/r` | Regenerate the previous GM response |
| `/quit` | Quit without saving |
| `/help` or `/h` | List commands |

---

## Requirements

- Python 3.10 or later
- [LM Studio](https://lmstudio.ai/) (running as a local server)
- Recommended model: Gemma4 12B
- Recommended context length: 32,768 tokens or more (input side: about 10,000 tokens of system prompt plus the conversation history as the story progresses, about 30,000 tokens in total; output side: `MAX_TOKENS` is the cap for a single GM generation, and actual output is a few hundred to about 1,000 tokens)

## Setup

There is no binary distribution. Download the source code and run it as is.

```bash
git clone https://github.com/naoki-Kamishiro/narrative-interact.git
cd narrative-interact
pip install -r requirements.txt  # openai / json-repair
```

Set the LM Studio endpoint in `config.py`.

```python
# config.py
LM_STUDIO_URL = "http://localhost:1234/v1"  # LM Studio's default URL
MAX_TOKENS    = 1024                         # Maximum tokens output per generation
TEMPERATURE   = 0.85
```

You do not need to specify a model ID (LM Studio automatically uses the loaded model).
Change the context length (32,768 tokens or more recommended) in LM Studio's model settings.

---

## Auto-play (for debugging)

A mode where an LLM also handles the player's input. Used for prompt verification and behavior checks.

```bash
python main.py --normal           # Normal mode
python main.py --deviate          # Deviate mode (actions that deliberately go beyond GM constraints)
python main.py --debug            # Manual play with debug output
python main.py --normal --batch 5   # Batch run (5 consecutive runs with random genres and titles)
python main.py --deviate --batch 5  # Batch run in deviate mode
```

With `--batch N`, genres are picked in random order from a fixed list (12 genres), the LLM generates a title each time, N sessions run back to back, and a JSON file is saved after each one. The story's axis, whether to use dice, the difficulty, and the GM one-liner are chosen once at launch and shared across all sessions.

The player LLM's behavior depends heavily on the model, genre, and plot settings. In particular, when genre constraints turn off combat, exploration, and puzzle-solving entirely (ensemble drama, slice of life, etc.), the player LLM tends to fall into loops of repeating actions such as "gaze at" or "approach." This is not a system bug but the model's natural behavior in genres with a narrow range of possible actions.

If you use auto-play for research or observation, genres with exploration and puzzle-solving, such as dark fantasy, horror, and mystery, tend to produce more varied behavior.

---

## Model limitations (compromises with Gemma4 12B)

These may improve with a more capable model. Each item's status falls into one of three categories:
- **Mitigation implemented**: Prompts or processing have been added to reduce how often it occurs
- **Remaining constraint**: Still occurs at some frequency after mitigation
- **Model-dependent**: Mitigated, but full resolution depends on the model's ability

**Mitigation implemented (mostly suppressed, but occurs probabilistically)**

- **Ending every turn with a question**: The GM tries to close every turn with "What do you do?" or "Where will you go next?" Suppressed by a prohibition rule
- **Listing choices as bullet points**: The GM lists options such as "A. Run B. Fight C. Negotiate." Suppressed by a prohibition rule
- **Ignoring or rewriting dice results**: The GM narrates what is effectively a success on a failed roll, or immediately nullifies a successful roll. Suppressed by consistency rules
- **Sinking into a single moment**: The GM keeps digging into the same scene or the same target, and the story does not move forward. Suppressed by repetition-limit rules
- **NPCs voicing the protagonist's inner life**: An NPC delivers lines that thematically explain the meaning of the protagonist's actions, such as "You've truly grown." Suppressed by a prohibition rule
- **Premature endings**: The GM ends the story on everyday narration such as "went home" or "rested." Suppressed by more detailed ending conditions

**Remaining constraints (still occur at some frequency after mitigation)**

- **Inner life and meaning creeping into the narration**: The GM writes emotional or inner descriptions such as "pride dwells within" or "resolve hardens," or interpretations such as "this means X." Suppressed by a prohibition rule, but it can break down in the later part of long stories or at the climax
- **Anticipating the landing point**: Motive or theme words written in the plot's ending field (such as "obsession" or "what they wanted to protect") start appearing in NPC dialogue or narration before the ending. Suppressed by a prohibition rule and an instruction to exclude motive words from the ending field, but it tends to occur in genres where motive is the core of the story, such as mystery

**Model-dependent (mitigated, but full resolution depends on the model's ability)**

- **Adding new settings first**: Each time it narrates the result of an action or roll, the GM adds new settings, threats, or characters instead of deriving the result from information already established. The story tends to feel like it grows in setting volume rather than complexity, and cause-and-effect becomes thin. Suppression rules have been added
- **Uniformly large outcome magnitude**: Success, failure, decisive success, and severe failure all tend to trigger large-scale developments that shake the whole story. The strength of the roll is not reflected in the scale of the result, and the sense of consequence from choices can become monotonous

---

## Known issues

- **Loops during auto-play**: The player LLM sometimes repeats actions on the same target while subtly changing the verb, such as "grip → clench → put force into." Suppressed by adding to the player prompt: "If actions on the same target continue three times with different verbs, switch to a different target or location." Full resolution is model-dependent.
- **Inner-life actions by the player LLM**: During auto-play, the player LLM sometimes outputs inner actions such as "make up one's mind" or "convey one's gratitude." Suppressed by adding to the player prompt: "Do not output inner actions that cannot be observed from outside."
- **Bringing in items from outside the setting**: During auto-play, the player LLM sometimes brings in items or means that do not exist in the story's world (e.g., using a gun in medical horror). Suppressed by adding to the player prompt: "Do not use items or means from outside the story's world."
- **Fixation on failed targets**: During auto-play, the player LLM sometimes keeps trying the same target even after repeated failures, without switching to another target or location. Suppressed by adding to the player prompt: "If you fail twice in a row on the same target, switch to a different target."
- **Target-renaming loops by the player LLM**: During auto-play, the player LLM sometimes repeats essentially the same action on the same group while changing the target's name slightly each time, such as "Soldier A," "heavy soldier," "soldier in front." The existing rule ("after three consecutive actions on the same target, move elsewhere") judges individual targets, so it has a loophole when facing a group. Full resolution is model-dependent.
- **Hook closing tends to be skipped at the ending**: The closing of the opening hook (hook.closing) is sometimes not narrated in the ending or epilogue. Suppressed by instructing "include this in the narration of the landing point" in both the [Plot] section and the [Closing and lingering aftertaste] section of the GM prompt. Full resolution is model-dependent.

---

## License

MIT
