---
name: hersona-initializer
description: Initializes hersona persona on first use of a profile and assists in maintaining the applied speech style if deviation is detected during conversation.
version: 0.0.2
author: shiro-0x
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hersona, persona, initialization, maintenance, enforcement]
    category: personality
    requires_toolsets: []
---

# hersona-initializer

## 概要
プロフィール初回使用時にhersonaを自動適用し、会話中に口調が崩れかけた場合の辅助も行うスキルです。

## 主な機能
- 初回メッセージ時に自動でデフォルトペルソナを適用
- 口調の崩れを辅助的に检知・修正する機能（将来的な拡張含む）
- 手動での再適用コマンドを提供

## コマンド
```bash
/hersona init          # 手動でペルソナを再適用・強化
/hersona init --force  # 強制的に再適用
```

## 推奨設定
プロフィールの `SOUL.md` に以下を記述してください：

```markdown
## Hersona Default Settings
Default command: /hersona personality/tsundere speech/keigo multi --weight moderate
```

この記述を読み取り、初回適用および必要に応じた再適用を行います。