# Hermes Agent Integration Guide

This guide explains how to use hersona effectively with [Hermes Agent](https://hermes-agent.nousresearch.com/).

## Installation

```bash
# Add this repository as a tap
hermes skills tap add shiro-0x/hersona

# Install the core skills
hermes skills install hersona
hermes skills install hersona-initializer
```

## Recommended Profile Builder Setup

### Step 1: Create Profile
Use Profile Builder to create a new profile.

### Step 2: Enable Skills
Enable the following skills:
- `hersona`
- `hersona-initializer`

### Step 3: Configure SOUL.md (推奨: `hersona soul` または `hersona persistent`)

**方法 A: `hersona soul` で SOUL.md を直接書き出す (ROADMAP §⑤)**

```bash
hersona soul personality/tsundere speech/keigo \
  --weight moderate \
  --profile default \
  --force
# → ~/.hermes/profiles/default/SOUL.md に公式 4 要素 (name / personality /
#   tone / behavioral guidelines) が書き出される
```

**方法 B: `hersona persistent` で SOUL.md 自動書き出し + config.yaml ブロック表示 (ROADMAP §⑤.1)**

```bash
hersona persistent personality/tsundere speech/keigo \
  --weight moderate \
  --profile default \
  --force
# → SOUL.md 自動書き出し
# → config.yaml 追記用 YAML ブロックを表示 (手動で貼り付け)
```

**方法 C: 旧来通り SOUL.md に直接記述 (手動運用)**

```markdown
## Hersona Default Settings
Default command: /hersona personality/tsundere speech/keigo multi --weight moderate
```

**推奨**: 方法 A または B。`hersona persistent` を使うと 1 コマンドで SOUL.md 更新と
ペルソナレジストリ反映の両方を取得できる。
直接 `set` 操作でレジストリを書き換えるのは Pitfall 回避のため実装していないので、
登録はフレームワークの永続化 API 経由で行うこと。

**Recent Context (セッション跨ぎ memory)**:

```bash
hersona soul personality/tsundere \
  --memory '{"last_topic": "ReAct", "mood": "やや真剣"}' \
  --force
# → SOUL.md 末尾に「## Recent Context」セクションが追加される
```

memory の内容は hersona が生成しない (LLM 抽出等は呼び出し元 / Hermes の責務)。
`hersona persistent` でも同様に `--memory` / `--memory-file` が使える。

### Step 4: First Message
Send any message to the agent. `hersona-initializer` will automatically apply the default persona on first use.

## Useful Commands

| Command | Description |
|---------|-------------|
| `/hersona list` | List available attributes |
| `/hersona personality/tsundere speech/keigo multi --weight moderate` | Apply blended persona |
| `/hersona recommend` | Get recommended blend |
| `/hersona measure --text "..." --weight moderate` | Check output intensity |
| `/hersona soul <attrs...> --force` | Write SOUL.md to `~/.hermes/profiles/<name>/SOUL.md` (Hermes One official spec) |
| `/hersona persistent <attrs...> --force` | Persist: SOUL.md auto-write + print config.yaml block |
| `/hersona init` | Manually initialize hersona |

## Multiple Personas

If you want to use different personas, create separate profiles (e.g. `tsundere-poster`, `kuudere-research`).

## Tips for Production Use

- Always enable **Write Gate** for profiles that perform external actions (posting, file operations, etc.)
- Use Docker or Modal backend for better isolation
- Use `hersona measure` before automated posting
