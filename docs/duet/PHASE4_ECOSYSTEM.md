# Phase 4 詳細設計: 生態系接続

> 実装先: hersona-duet (一部 hersona)。依存: Phase 2 (4.1, 4.2, 4.4) / Phase 3 (4.3)。
> 4 つのサブプロジェクトは独立しており、別エージェントが並行実装できる。

---

## 4.1 Hermes Agent アダプタ (`/duet` スキル)

### 構成

```
adapters/hermes/
├── SKILL.md              # Hermes スキル定義 (hersona の skills/hersona/SKILL.md と同形式)
└── bridge.py             # スキルコマンド → duet API の薄い橋
```

### コマンド体系

```
/duet                          # ヘルプ + プロジェクト状態
/duet cast                     # 配役一覧 (conflict 警告込み)
/duet run <scene_id>           # 完全自動でシーン実行 → 台本体を出力
/duet join <scene_id>          # 参加モード: 以降のユーザー発話を human_utterance として扱う
/duet review <run_id> ok       # 承認
/duet review <run_id> retake <beat> "<note>"
```

### 仕様

- bridge は Phase 1/2 の Python API (`run_scene` / `retake` / `QueueInputSource`) を呼ぶだけ。
  ロジックを持たない (core 共有原則)
- join モード中の終了語: `/duet leave`。Hermes 側の会話とシーン内発話の混線を防ぐため、
  join 中は他コマンドを受けたら確認を挟む
- 受け入れ基準: Hermes 上で `/duet run shopping_01` が台本を返す (live)

---

## 4.2 ギャルゲーパック (v1 構想の回収)

### 概要

duet 本体に**変数システム**を最小追加し、「好感度 → weight」をパック定義だけで
実現する。エンジンに恋愛固有のコードは入れない。

### 変数システム (duet 本体への追加・汎用)

```yaml
# project.yaml 追加フィールド
variables:
  affection_rinka: { initial: 30, min: 0, max: 100 }

# scene.yaml 追加フィールド
on_scene_end:                       # シーン承認時に writer が JSON で増減を判定
  - var: affection_rinka
    rubric: 凛花の健太への好意が深まる言動があれば +5〜+15、傷つく言動は -5〜-15
actors_override:                    # シーン開始時に変数から weight を導出
  - id: rinka
    weight_from: { var: affection_rinka }   # hersona.weight_for_score (P0-3) を使用
```

### 仕様

- `weight_from` は `weight_for_score(score, previous=前シーンのlevel)` を呼ぶ
  (ヒステリシスでシーン間の振動を防ぐ)
- 変数更新は**承認 (approve) 時のみ**確定 (リテイクで巻き戻る事故を防ぐ)
- 変数値は `runs/` とは別に `saves/<project>/state.json` に保存 (= プレイデータ)
- ルート分岐: scene.yaml に `requires: { affection_rinka: ">= 60" }` を許可。
  満たさないシーンは一覧でロック表示 (UI) / 実行時エラー (CLI)
- サンプルパック `packs/examples/galge/`: ヒロイン 2 人 (属性ブレンドのみ・固有名詞なし)、
  共通 3 シーン + 分岐 2 シーン + エンディング 2 種
- 受け入れ基準: 好感度の上昇で凛花の weight が strong→moderate に変化し、
  口癖露出が目に見えて変わることを live 確認

---

## 4.3 公開ギャラリー (GitHub Pages)

- `duet export --site <dir>`: 承認済み台本を静的 HTML (台本体/小説体) に変換
- 公開前ゲート: `find_proper_noun_risks` (hersona) を全文に適用し、検出時は
  確認プロンプト。`--force` なしでは出力しない
- hersona の X グロース施策と連動: 出力 HTML に OGP (タイトル+ログライン) を付与
- 受け入れ基準: Pages にデプロイした台本ページが OGP 付きでシェアできる

---

## 4.4 Character Card V2 インポータ

### 目的

SillyTavern 圏の既存キャラカード資産から duet の配役 (hersona ブレンド) への流入動線。

### CLI

```
duet import card <card.png|card.json> [--out actors_fragment.yaml] [--save-custom]
```

### 変換パイプライン

1. **パース**: PNG の tEXt チャンク (`chara` キー、base64 JSON) または素の JSON を読み、
   `spec: chara_card_v2` を検証。対応フィールド: `name / description / personality /
   first_mes / mes_example`
2. **属性推定** (LLM 1 回): description+personality を入力に、hersona の属性一覧
   (id + description_en) から **最大 4 個のブレンドと weight を JSON で選定**させる。
   出力契約: `{"blend": ["tsundere", ...], "weight": "moderate", "confidence": 0-1,
   "unmatched_traits": ["..."]}`
3. **補完 (任意 `--save-custom`)**: `unmatched_traits` が多い場合、
   `hersona.build_attribute` + `save_attribute` でユーザー名前空間にカスタム属性を生成
   (スキーマ検証ゲート・固有名詞ガードは hersona 側に従う)
4. **出力**: project.yaml に貼れる actor フラグメント。`confidence < 0.5` は
   警告と手動確認を促す

### 注意 (文書化必須)

- カードの権利状態は不明なものが多い。インポート結果の**共有時**は
  `assert_shareable` を通す (ローカル利用は自由 — hersona と同方針)
- 受け入れ基準: 公開配布されているテスト用カード 3 枚で blend が生成され、
  `duet validate` を通る actor フラグメントが得られる

---

## 4.5 実装順の推奨

```
4.2 ギャルゲーパック (本体価値の証明・X 映え)
 → 4.3 ギャラリー (グロース接続)
 → 4.1 Hermes アダプタ (生態系の入口)
 → 4.4 カードインポータ (外部コミュニティ流入)
```
