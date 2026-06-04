# コントリビュートガイド

hersona プロジェクトへの貢献ありがとうございます。

## 開発フロー

```
セリフ収集（collector）→ 性格プロファイル生成（writer）→ 検証・push（publisher）→ レビュー（リブラ）
```

各段階を別エージェントが担当します。個人が全工程を行う場合は順番に実施してください。

## データ追加

### 1. セリフ収集

`data/<作品名>/<キャラ>_lines.md` にセリフ集を保存：

```markdown
# <キャラ名> セリフ集

> 出典: <Wiki名> (<URL>)
> ライセンス: CC BY-SA 4.0

## 通常時
1. 「セリフ1」
2. 「セリフ2」

## 戦闘時
...

## イベント時
...
```

- 1キャラあたり 30-50本を目安
- セリフは原文ママ、勝手な翻訳・改変禁止
- 出典URL必須

### 2. YAML生成

`prompts/generate_character.md` のプロンプトを使い、YAMLを生成。
`schema/character.schema.json` に準拠。

### 3. Markdown生成

人間可読なMarkdownを生成。セリフ引用を10-20件含める。

### 4. 検証

```bash
python scripts/validate.py
```

全YAMLファイルが検証される。エラーが出たら修正して再実行。

### 5. コミット・push

```bash
git add data/<作品名>/<キャラ>.{yaml,md}
git commit -m "add: <キャラ名> (<作品名>) character profile"
git push origin main
```

## プルリクエスト

PRテンプレートに従って記載。review 待ち。リブラが承認したらマージ。

## ライセンス方針

- セリフ引用は各Wiki記事のライセンス（多くはCC BY-SA）を継承
- 二次創作研究目的、商用利用は不可
- キャラ自体の権利は原作者・制作会社に帰属
- 引用は30-50本/人まで（多すぎると引用氾濫）

## 質問・相談

GitHub Issue で。ラベル `question` を付けてください。
