# Narrative Interact

> ⚠️ This project is under development. Unexpected behavior or bugs may occur.

> **Language note:** You can choose Japanese or English at launch. In English, the UI and the GM's narration are in English. The internal prompts stay in Japanese.

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

Right after launch, choose the language (日本語 / English). Use `python main.py --lang en` (or `--lang ja`) to skip this choice.

Then enter the following in order.

```
Genre: Mystery
Title: The Missing Will
```

Next, choose the story's axis.

| Choice | Mode | Description |
|------|--------|------|
| 1 | Plot-guided, strong | Twists, choices, and failures are resolved as the plot dictates. The player's freedom of action is preserved while nearly all major plot elements are resolved. **Recommended for first-time play** |
| 2 | Plot-guided, adaptive | Follows the plot but allows deviation. If the deviation becomes large, the story is reconstructed from the current situation and guided to a landing. |
| 3 | Plot-guided, free | The plot is reference only. Deviation is fine. Suited for putting the player's free actions first. |
| 4 | No plot, improv | No plot is generated; the GM improvises the story. No constraints on where the story goes. |

Next, choose whether to use dice resolution (Y/n). If you use it, also choose the difficulty (easy / normal / hard).

Finally, choose whether the GM one-liner is on or off.

| Choice | Behavior |
|------|------|
| On (cynical) | At turning points, the GM makes a cynical one-line comment, such as "Well, that's one way to do it" or "...I see." |
| Off | The GM proceeds silently (the original behavior) |

**About the differences between modes**

Each mode differs in how strongly the plot constrains the GM. The same player actions can lead to very different endings depending on the mode. This difference is intentional by design.

- **Strong**: The system injects a beat (a story milestone) into the GM every turn and forces the plot to be resolved. After a choice is posed, the next turn is spent narrating the result of that choice, and the climax scene is narrated over two turns before the story heads to its ending
- **Adaptive**: Deviation is checked every turn. After a cumulative 3 deviation judgments, an instruction encouraging convergence is injected; after a cumulative 5, the LLM regenerates a new plot and beat control guides the story to a landing (the count is not reset by turns without deviation). If the player keeps deviating from the start, the story finishes soon after regeneration and ends up short (by design)
- **Free**: The plot is only passed to the GM as reference in the system prompt; no beats are injected. Deviation is never forced back
- **Improv**: No plot generation and no beat injection; the story advances on the GM's output alone

In free, improv, and adaptive (before regeneration), an instruction to bring the story to a close is injected into the GM once the story exceeds 25 turns.

**About the GM one-liner**

The GM one-liner runs as a separate call, independent of story generation. It has no effect on the story's rules, mode, or beat progression.

The GM comments only at turning points (plot milestones, or turns the LLM judges to be turning points). Because it does not appear every turn, it carries meaning when it does. Depending on the genre and how the story develops, there may be few turning points and the one-liner may rarely appear.

In the console, `GM:` is shown in blue and the comment text in cyan, for example `GM: Well, that's one way to do it.`

### 2. Entering actions

Read the GM's narration and type an action as the protagonist.

```
> Open the desk drawer.
> Talk to the old man.
> Look out the window.
```

Actions are free-form. The GM does not reject the player's actions; it changes the world as a result of them.

The world moves even if the player does nothing. Just watching or waiting still lets the story advance through the passage of time and the decisions of other characters (if you don't choose when a choice is posed, the result of not choosing is narrated).

### 3. Dice resolution

If dice resolution is enabled, some actions trigger a dice roll, and the outcome is reflected in the GM's narration. The difficulty can be chosen at launch (easy / normal / hard).

The roll is decided by Python's `random.randint(1, 20)`. The AI only decides "whether a roll is needed" and "how to classify the action's risk and uncertainty"; it has no involvement in the roll or the difficulty numbers. The GM receives only the outcome and instructions matching its strength, not the numbers (the roll and difficulty are recorded in the JSON log).

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
- Recommended model: Gemma4 12B (regular build)
  - The Gemma4 12B QAT build has also been tested. However, a single word in English or another language may slip into the text. This does not affect how the story progresses
  - gemma-4-26B-A4B (IQ3_XXS) has also been tested
  - gemma-4-31B-it (IQ2_M) has also been tested. However, it is very slow on a machine with 16GB VRAM and 64GB RAM and is not practical there
- Recommended context length: 32,768 tokens or more (input side: about 10,000 tokens of system prompt plus the conversation history as the story progresses, about 30,000 tokens in total; output side: `MAX_TOKENS` is the cap for a single GM generation, and actual output is a few hundred to about 1,000 tokens)

## Setup

There is no binary distribution. Download the source code and run it as is. Use either of the following.

**With Git**

```bash
git clone https://github.com/naoki-Kamishiro/narrative-interact.git
cd narrative-interact
pip install -r requirements.txt  # openai / json-repair
```

**As a ZIP download (no Git needed)**

1. On the [GitHub page](https://github.com/naoki-Kamishiro/narrative-interact), click the green "Code" button and choose "Download ZIP"
2. Extract the ZIP (the folder is named `narrative-interact-main`)
3. Run the following in the extracted folder

```bash
cd narrative-interact-main
pip install -r requirements.txt  # openai / json-repair
```

To update a ZIP install, download it again the same way. To keep your saves and logs, move the `saves/` and `logs/` folders from the old folder into the new one.

Set the LM Studio endpoint in `config.py`.

```python
# config.py
LM_STUDIO_URL = "http://localhost:1234/v1"  # LM Studio's default URL
MAX_TOKENS    = 1024                         # Maximum tokens output per generation
TEMPERATURE   = 0.85
REASONING_EFFORT = "none"                   # Turns off reasoning ("thinking"), even for models that reason, such as QAT builds
```

`REASONING_EFFORT` stops reasoning in models that reason (such as the QAT build of Gemma4), cutting wait time and token use. It also works as-is with the regular non-reasoning build. If it causes problems, set it to `None` and the setting will not be sent.

You do not need to specify a model ID (LM Studio automatically uses the loaded model).
Change the context length (32,768 tokens or more recommended) in LM Studio's model settings.

---

## Auto-play (for debugging)

A mode where an LLM also handles the player's input. Used for prompt verification and behavior checks.

```bash
python main.py --normal           # Normal mode
python main.py --deviate          # Deviate mode (actions that leave the story, such as ignoring the GM's lead and changing location)
python main.py --debug            # Manual play with debug output (the session log is overwritten as JSON in the logs/ folder after every action)
python main.py --normal --batch 5   # Batch run (5 consecutive runs with random genres and titles)
python main.py --deviate --batch 5  # Batch run in deviate mode
python main.py --normal --batch 1 --lang en  # Batch run in English
```

With `--batch N`, genres are picked in random order from a fixed list (12 genres), the LLM generates a title each time, N sessions run back to back, and a JSON file is saved after each one. The story's axis, whether to use dice, the difficulty, and the GM one-liner are chosen once at launch and shared across all sessions.

The player LLM's behavior depends heavily on the model, genre, and plot settings. In particular, when genre constraints turn off combat, exploration, and puzzle-solving entirely (ensemble drama, slice of life, etc.), the player LLM tends to fall into loops of repeating actions such as "gaze at" or "approach." This is not a system bug but the model's natural behavior in genres with a narrow range of possible actions.

If you use auto-play for research or observation, genres with exploration and puzzle-solving, such as dark fantasy, horror, and mystery, tend to produce more varied behavior.

---

## Known limitations (compromises with Gemma4 12B)

Larger models (gemma-4-26B-A4B, gemma-4-31B-it) keep the prose style better, but most of the issues below still appear.

**Mitigation implemented (still occurs probabilistically)**

- **Ending every turn with a question**: Closes turns with "What do you do?"
- **Bulleted choices**: Lists options such as "A. Run B. Fight" (in a choice scene, the GM or an NPC presenting two options within dialogue or narration is intended, as TRPG-style progression)
- **Ignoring dice results**: Narrates a failure as an effective success, or nullifies a success right after
- **Sinking into a single moment**: Keeps digging into the same scene, and the story stops moving
- **NPCs explaining or judging**: NPCs explain the meaning of the protagonist's actions or praise their decisions
- **Premature endings**: Ends the story on everyday narration such as "went home"
- **Resolving costs that never happened**: Adds injuries or losses in the epilogue that never occurred in the story, or rewrites the epilogue to match the plot's landing point instead of how the story actually ended, or adds new events in the epilogue aimed at the plot's goal
- **Skipping the hook closing**: The closing of the opening hook (hook.closing) is not narrated in the ending
- **Forced jumps to the landing point**: In free and adaptive modes, abruptly brings in characters who never appeared or distant places to match the landing point
- **Acting out the peak**: In strong mode, the GM writes the protagonist's peak action that is not in the input
- **Warping to the climax**: In strong mode, carries the protagonist to the climax setting via a flash of light or a collapse (during the two climax turns, a warp is detected and the turn is regenerated once)
- **Revealing twists**: A third-party NPC explains a plot twist at length in dialogue

**Remaining constraints (still occur at some frequency after mitigation)**

- **Meaning in the narration**: Inner life or interpretation such as "resolve hardens" or "this means X" creeps in. More common late in the story and at the climax
- **Anticipating the landing point**: Uses motive or theme words from the plot's ending before the ending. Common in mystery
- **Exceeding the length guideline**: Ignores the 300-character-per-turn guideline, sometimes by a lot depending on genre
- **Copying the landing point**: Copies the plot's landing-point text almost verbatim at the close of the ending
- **Rewriting the location at the climax**: In strong mode, the scenery at the current location turns into the climax setting ("the walls crumble and it transforms into a plaza")
- **Repeated closing scene**: Finishes the closing scene but forgets the ending marker, then writes the same scene again the next turn
- **Reading intent into the hold turn**: In strong mode, on the turn after a choice is posed, interprets the action as "a sign of resolve" in narration or NPC dialogue

**Model-dependent (full resolution depends on the model's ability)**

- **Adding new settings first**: Adds new settings, threats, or characters instead of deriving results from what is already established
- **Uniformly large outcomes**: Triggers story-shaking developments regardless of how strong the roll was (often it is a plot milestone advancing in the same turn, rather than the roll result itself, that makes the outcome look large)
- **Ignoring genre constraints**: Creates hostile developments even in genres where combat is disabled, often triggered by a severe failure
- **Epilogue contradicting the story**: Occasionally narrates the opposite of the player's choice, or a plot loss that never appeared in the story, in the epilogue (showing a later moment as the outcome of something already set in motion in the story is by design)
- **Rewriting the player's input**: Narrates a different action from the one entered, to make things fit
- **Plot labels leaking**: Labels from the plot (such as "the third party") may appear in the text
- **Addressing the protagonist**: The narration sometimes refers to the protagonist as "you"

---

## Known issues (player LLM during auto-play)

All are suppressed through the player prompt (except the target-renaming loop, which has no mitigation). Full resolution is model-dependent.

- **Verb-changing loops**: Repeats actions on the same target while changing the verb, such as "grip → clench → put force into"
- **Target-renaming loops**: Repeats actions on the same group while changing what it is called, such as "Soldier A" or "heavy soldier"
- **Fixation on failed targets**: Does not switch to another target or location after repeated failures
- **Inner-life actions**: Outputs actions that cannot be seen from outside, such as "make up one's mind"
- **Means from outside the setting**: Brings in items or means that do not exist in the world, such as a gun in medical horror

---

## License

MIT
