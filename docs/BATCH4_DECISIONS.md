# Batch 4 属性追加 — 決定記録

> Batch 3 の積み残し (未採用 3 種) の判断と、新規 5 種の方向性に関する設計合意の記録。
> 確定日: 2026-06-09。属性数 **52 → 59** (personality 17→20 / speech 16→20)。

## 0. サマリ

| 区分 | 確定内容 |
|---|---|
| 積み残し判断 | **seductive / stutter を採用**、energetic_exclamatory / archaic は skip |
| 新規 5 種の方向 | **F: 新カテゴリを作らず speech / personality に新軸を純加算** |
| 除外 | C (physical_feature → visual) は見送り。A/B/D の新カテゴリは開設しない |
| 影響範囲 | YAML 7 ファイル追加のみ。schema / core ロジックは不変、テストの数量アサーションのみ更新 |

---

## 1. 積み残し 3 種(+1)の判断

Batch 3 提案 15 種のうち未採用だった 3 種、および関連する archaic の扱い。

| 提案 | カテゴリ | 判断 | 軸 / 理由 |
|---|---|---|---|
| **seductive**(誘惑・色気) | speech | **採用** | 「直接的な色気・誘惑」軸。mischievous(戦略的からかい)・princess_speech(気品)とは別。色気軸は glamorous(visual)/princess_speech とも近接するため、`conflicts_with` と `notes` で直截さを明示して差別化する |
| **stutter**(吃り・言い淀み) | speech | **採用** | 「流暢さ(fluency)の乱れ」軸。whispery(声量)・soft(甘さ)とは独立した真の新軸 |
| **energetic_exclamatory**(超元気) | speech | **skip** | personality の genki(weight=strong)と冗長。同軸属性の重複を避ける |
| **archaic**(古風) | speech | **skip** | 提案 archaic は **既存の `attributes/speech/archaic.yaml` と重複**。(当初「princess_speech で置換済」とされていたが、実際は archaic 属性が現存しているため重複が正しい理由) |

→ 採用 **2 種** (seductive / stutter) / skip **2 種** (energetic_exclamatory / archaic)。

---

## 2. 新規 5 種の方向性

### 検討した選択肢

| 案 | 内容 | 判断 |
|---|---|---|
| **C** physical_feature | tall / long_hair などを既存 visual に追加 | **見送り**(visual は今回扱わない) |
| **F** speech/personality 深掘り | 新カテゴリを作らず既存 2 カテゴリに新軸追加 | **採用** |
| **A** relationship_type(新カテゴリ) | childhood_friend_v2 / ex_partner 等 | 見送り |
| **B** emotional_state(新カテゴリ) | cheerful / angry 等の一時的感情 | 見送り |
| **D** lifestyle(新カテゴリ) | urban / salaryman 等 | 見送り |

### 新カテゴリ(A/B/D)を見送った理由

- **schema enum がロック**: `attribute_category` は personality / speech / archetype / visual / hobby の 5 種固定 (`schema/attribute.schema.json`)。新カテゴリ追加は schema 改訂に加え CompatibilityMatrix / render_blend / weight / CLI / docs まで波及する。Batch 4 は純加算に留め、低リスクを優先。
- **A (relationship_type)**: `archetype` の childhood_friend / rival / mentor が実質「関係性」属性であり、境界が重複。新カテゴリ開設前に「役割 vs 二者関係」の切り分け定義が必須。→ 別バッチ案件。
- **B (emotional_state)**: 現行 weight は「持続的特性がどれだけ強く出るか」の軸で、一時的感情とは意味論が噛み合わない。attribute ではなくセッション内 mood 機構として別設計すべき。
- **D (lifestyle)**: archetype / 設定寄りで合成価値が薄い。優先度最低。

### 採用した 5 種(F)

| # | 属性 | カテゴリ | 軸 | 既存との非重複根拠 |
|---|---|---|---|---|
| 1 | **blunt**(ぶっきらぼう) | speech | 言葉数・素っ気なさ | tomboy(ボーイッシュ)/ ore_boy(一人称)とは別。theatrical の対極 |
| 2 | **theatrical**(芝居がかり) | speech | 大仰・過剰演出 | princess_speech(気品)/ archaic(古風)とは別の「演出過剰」 |
| 3 | **chuunibyou**(中二病) | personality | 誇大な自己設定 | mysterious(寡黙な神秘)とは逆の自己申告型誇大 |
| 4 | **narcissist**(ナルシスト) | personality | 自己愛 | glamorous(見た目)はレイヤ別。princess の自尊とも別核 |
| 5 | **optimist**(楽観的) | personality | 見通しの明るさ | pessimist の対極。genki(テンション)とは別軸 |

---

## 3. 実装と影響

- **追加ファイル(計 7)**
  - speech: `seductive` / `stutter` / `blunt` / `theatrical`
  - personality: `chuunibyou` / `narcissist` / `optimist`
- **検証**: `scripts/validate.py` 全件 pass(exit 0)、conflict は対称閉包で解決。
- **テスト**: 数量アサーションを 52→59(personality 17→20 / speech 16→20)に更新。全 276 pass。
- **凍結生成物は不変**: `scripts/_oneoff/gen_v1_attributes.py` は docstring が「Batch 3 完結: 52 属性」と明記する Batch 3 の凍結スナップショット(テストからは未実行・内部的に 52 で自己完結)のため変更しない。Batch 4 分は手書き YAML として追加した。

## 4. フォローアップ(対応済み)

- `hersona recommend` 診断クイズに Batch 4 の 7 属性への到達経路を追加(2026-06-09)。
  - 新設 2 問: `tone`(声や口調の色 → seductive / stutter / blunt / theatrical)/
    `selfview`(自分の捉え方 → chuunibyou / narcissist / optimist)
  - 既存 speech 質問(6 択)の肥大化を避け、専用質問として分離
  - `test_recommend.py` に 7 属性の到達経路テストを追加(`washi` / `kyoto_ben` の慣習に倣う)
