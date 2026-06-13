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

### Step 3: Configure SOUL.md
Add this to your profile's `SOUL.md`:

```markdown
## Hersona Default Settings
Default command: /hersona personality/tsundere speech/keigo multi --weight moderate
```

### Step 4: First Message
Send any message to the agent. `hersona-initializer` will automatically apply the default persona on first use.

## Useful Commands

| Command | Description |
|---------|-------------|
| `/hersona list` | List available attributes |
| `/hersona personality/tsundere speech/keigo multi --weight moderate` | Apply blended persona |
| `/hersona recommend` | Get recommended blend |
| `/hersona measure --text "..." --weight moderate` | Check output intensity |
| `/hersona init` | Manually initialize hersona |

## Multiple Personas

If you want to use different personas, create separate profiles (e.g. `tsundere-poster`, `kuudere-research`).

## Tips for Production Use

- Always enable **Write Gate** for profiles that perform external actions (posting, file operations, etc.)
- Use Docker or Modal backend for better isolation
- Use `hersona measure` before automated posting
