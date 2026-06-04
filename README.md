# hersona

> アニメ・ゲーム・漫画キャラの口調・性格プロファイル集
> AIエージェント（Hermes Agent 等）で `/personality` プリセットとして使える

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

## 概要

アニメ・ゲーム・漫画キャラクターの **口調・性格・語彙** を体系的にデータベース化し、AIエージェントの system prompt に注入できるプロファイルとして配布するオープンソースプロジェクト。

各キャラは構造化データ（YAML）と人間可読ドキュメント（Markdown）の両形式で提供され、Hermes Agent の `/personality` 機能、または他のLLMベースのチャットエージェントで利用できる。

## 使い方

### Hermes Agent で使う

`~/.hermes/config.yaml` の `agent.personalities` に追加：

```yaml
agent:
  personalities:
    melina: |
      あなたはエルデンリングのメリーナです。
      [data/elden-ring/melina.md の中身を貼り付け]
```

または `/personality` コマンドで一時切り替え。

### 他の LLM で使う

`data/<作品>/<キャラ>.md` の内容を system prompt にそのまま入れる。YAML は機械可読・解析用。

## 収録作品

- [エルデンリング (ELDEN RING)](./data/elden-ring/)

## データ形式

```
data/
└── <作品名>/
    ├── _index.md            # 作品紹介・キャラ一覧
    ├── <キャラ名>.yaml      # 構造化プロファイル（機械可読）
    └── <キャラ名>.md        # 人間可読プロファイル（引用付き）
```

### YAML スキーマ

[schema/character.schema.json](./schema/character.schema.json) を参照。

## ライセンス

- **プロファイル本文**: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **セリフ引用元**: 各キャラの `metadata.sources` フィールドに明記（原則 Wiki 記事の CC BY-SA を継承）
- **キャラ自体の権利**: 各作品の著作権者に帰属（本プロジェクトは二次創作研究目的）

## コントリビュート

1. データ追加は `data/<作品名>/<キャラ名>.{yaml,md}` 形式で
2. セリフ引用は出典URL必須（Wiki記事ライセンス継承）
3. PR前に `python scripts/validate.py` で検証

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。

## 関連リンク

- リポジトリ: https://github.com/shiro-0x/hersona
- 関連スキル: hersona-collector / hersona-writer / hersona-publisher
