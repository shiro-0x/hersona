---
name: hersona
description: Anime-style character attribute system for Hermes Agent. Dynamically apply and blend personality traits (tsundere, kuudere, yandere, etc.), speech styles (keigo, gyaru, kansai-ben, etc.), and archetypes via simple slash commands. Supports multi-attribute blending and intensity control.
version: 1.1.0
author: shiro-0x
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [persona, character, anime, roleplay, japanese, tsundere, keigo, personality, archetype, speech]
    category: personality
    requires_toolsets: []
---

# hersona

## 概要

アニメ・ゲーム風のキャラクター属性を動的に適用できるスキルです。
性格（Personality）、口調（Speech）、役割（Archetype）を自由に組み合わせることができます。

## 主な機能

- 単一または複数の属性をブレンドして適用
- 属性の強度（mild / moderate / strong）を調整
- おすすめ属性の診断（レコメンド機能）
- 生成テキストの強度測定（measure）
- ユーザー独自のローカル属性作成・使用

## 利用可能なコマンド

| コマンド | 説明 | 例 |
|----------|------|----|
| `/hersona list` | 利用可能な属性一覧を表示 | - |
| `/hersona show <category>/<name>` | 属性の詳細を表示 | `/hersona show personality/tsundere` |
| `/hersona <category>/<name> single` | 単一属性を適用 | `/hersona personality/tsundere single` |
| `/hersona <attr1> <attr2> multi` | 複数属性をブレンド | `/hersona personality/tsundere speech/keigo multi` |
| `/hersona recommend` | 診断クイズで最適なブレンドを提案 | - |
| `/hersona measure --text "文章" --weight moderate` | 生成テキストの強度を測定 | 投稿前の品質チェックに便利 |
| `/hersona default` | 現在のペルソナを解除 | - |

## 使用例

```bash
# ツンデレ＋敬語を中程度で適用
/hersona personality/tsundere speech/keigo multi --weight moderate

# 強度を測定して品質を確認
hersona measure --text "ふん……別にあなたのためにやったわけではありませんわよ？" --weight moderate
```

## 対応カテゴリ

- **personality**: tsundere, kuudere, yandere, genki, chuunibyou など
- **speech**: keigo, gyaru, kansai_ben, kyoto_ben, onee_kotoba など（日本語・英語対応）
- **archetype**: childhood_friend, idol, rival, shrine_maiden, robot_android など

## 注意事項

- 属性は会話コンテキストに反映されます
- 複数のプロフィールで異なるペルソナを使い分けたい場合は、Profile単位で分けることを推奨します
- 自動投稿など外部連携を行う場合は、Write Gateの有効化を強く推奨します