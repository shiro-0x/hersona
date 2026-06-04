# キャラプロファイル生成プロンプト

セリフ集から hersona YAML/MD を生成するためのLLMプロンプトテンプレート。

## 使い方

1. `20_sources/<作品>/<キャラ>_lines.md` にセリフ集を準備
2. 以下のプロンプトにセリフ集を埋め込んで LLM に渡す
3. 出力を `data/<作品>/<キャラ>.yaml` および `<キャラ>.md` に保存

## プロンプト本体

```
あなたはアニメ・ゲームのキャラクター分析家です。
以下のセリフ集を分析し、キャラクターの性格・口調プロファイルを生成してください。

## キャラ情報
- 作品: {{作品名}}
- キャラ名: {{キャラ名}}
- セリフ出典: {{Wiki URL}}

## セリフ集
{{セリフ集をここに貼り付け}}

## 出力形式

### 1. YAML形式（character.schema.json に準拠）

```yaml
character_id: <作品>-<キャラ名>
name: <キャラ名>
source: <作品名>
source_url: <URL>
license: CC-BY-SA-4.0
license_source:
  - title: <Wiki名>
    url: <URL>
    license: CC-BY-SA-4.0
personality:
  core_traits:
    - <特性1>
    - <特性2>
    - <特性3>
  speech_style: <口調の説明>
  catchphrases:
    - "<口癖1>"
    - "<口癖2>"
  tone: <声の雰囲気>
  formality: <casual|polite|formal|archaic>
  vocabulary: <語彙特徴>
  emotion_baseline: <感情ベースライン>
  interaction_patterns:
    with_strangers: <初対面での挙動>
    with_friends: <親しい相手>
    under_stress: <ストレス下>
metadata:
  role: <物語上の役割>
  language_versions: [ja]
```

### 2. Markdown形式

人間可読なプロファイル。本文＋セリフ引用を10-20件含めてください。
```

## 注意事項

- セリフは原文ママ、勝手な改変禁止
- 推測と事実を区別する（明らかにセリフから導ける特性は「セリフより」、Wiki本文情報は「Wiki本文より」）
- 該当セリフがWiki本文に見つからない場合は `core_traits` に含めない
- 性格特性タグは3-7個に収める（多すぎると薄まる）
