---
name: hersona-initializer
description: Automatically applies default hersona persona on first use of a profile with reliable state management. Supports both automatic and manual initialization.
version: 1.1.0
author: shiro-0x
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hersona, persona, initialization, setup, automation]
    category: personality
    requires_toolsets: []
---

# hersona-initializer

## 概要

プロフィール初回使用時に、自動でhersonaのデフォルトペルソナを適用する初期化スキルです。

## 主な機能

- プロフィール初回メッセージ時に自動初期化
- 重複初期化の防止（状態管理）
- 手動初期化コマンド `/hersona init`
- `SOUL.md` に書かれたデフォルトブレンドを読み取って適用

## コマンド

```bash
/hersona init          # 手動初期化
/hersona init --force  # 強制再初期化
```

## 推奨設定方法

プロフィールの `SOUL.md` に以下を記述してください：

```markdown
## Hersona Default Settings
Default command: /hersona personality/tsundere speech/keigo multi --weight moderate
```

この記述を読み取って自動で適用します。