# hersona-duet 計画書 — 競合調査と開発プロジェクト計画

> 作成日: 2026-06-12 / ステータス: ドラフト（リポジトリ分離前の設計合意用）
> 対象: 「エージェント同士の1:1会話」と「自動生成型ギャルゲー」を担う
> **ギャルゲーシステム（エンジン）`hersona-duet`** を hersona と別リポジトリで開発する計画。
> hersona はライブラリ（属性・相性・weight・intensity の決定的コア）として依存される側に回る。

---

## 1. 競合調査（2026-06 時点）

### 1.1 軸A: エージェント同士のキャラクター会話

| プロジェクト | 形態 | 近さ | 評価 |
|---|---|---|---|
| **SillyTavern** | OSS ロールプレイ UI アプリ | ★★★ | グループチャットで複数キャラ（Character Card V2/V3）同士の会話が可能。コミュニティ最大。ただし**人間が遊ぶ UI アプリであり、組み込み可能なエンジン/ライブラリではない**。人格は散文ベースのカードで、属性の構造化・相性判定・強度測定・好感度状態機械を持たない |
| AITuberKit | OSS 配信/チャット Web アプリ | ★★ | 「AIキャラと話す」用途。人格は system prompt 直書き。エージェント対エージェントの対話制御やゲーム状態は対象外 |
| CAMEL / AutoGen / CrewAI | OSS マルチエージェント基盤 | ★ | role-playing はタスク遂行のための手段。エンタメ・キャラ性・日本語キャラ文化の語彙を持たない |
| SimsChat / llm-roleplay / PsyPlay / Neeko | 学術研究コード | ★★ | PsyPlay は Big-Five ベクトル + JSON ロールカードで概念的に最も近いが、研究再現用でありプロダクト/エンジンではない |
| Generative Agents / AI Town | OSS 社会シミュレーション | ★ | 多数エージェントの生活模倣。1:1 のドラマ設計やゲーム進行とは別物 |
| Inworld / Convai | 商用 NPC エンジン (SaaS) | ★★ | 「キャラ対話エンジン」としては最有力だがクローズド・従量課金・ゲームスタジオ向け。OSS・ローカル・ギャルゲー構造の領域は空いている |

### 1.2 軸B: LLM によるギャルゲー / ノベルゲーム生成

| プロジェクト | 形態 | 近さ | 評価 |
|---|---|---|---|
| **VinA** (vina-ai/vina) | OSS ビジュアルノベル生成器 | ★★★ | プロンプト→プロット/キャラ/立ち絵/Ren'Py 出力まで自動生成。ただし 2023 ハッカソン PoC のまま停止（Star 50）。**好感度・ルート・フラグ等のゲームメカニクスを持たない** |
| Ren'Py / HeartbeatEngine / ds-engine | OSS ノベルゲームエンジン | ★★ | 成熟したエンジンだが LLM 非統合。LLM 接続は個人 mod レベルで散発 |
| 国内個人実験 (note/Qiita のデモ群) | 個人デモ | ★★ | 「LLM が会話・選択肢・好感度変化を JSON で返す」構成のデモは複数存在。**いずれも一作品/一発デモで、再利用可能なエンジンとして公開されていない** |
| Red Ram (CEDEC 2024) ほか商用研究 | 商用/研究 | ★ | ミステリー自動生成等。ギャルゲー構造ではなく、OSS でもない |
| Anuttacon 等の AI ネイティブゲーム | 商用作品 | ★ | 「作品」であり「エンジン」ではない |

### 1.3 結論: 空白地帯（= duet のポジショニング）

> **「構造化属性で人格を定義し、好感度を weight に写像し、相性マトリクスでドラマを設計し、
> 強度測定でキャラ崩壊を検知する——決定的コアを持つ OSS ギャルゲーシステム」は存在しない。**

- 最近接の SillyTavern は「アプリ」、VinA は「死んだ PoC」、PsyPlay は「論文」。
  エンジン/ライブラリとしてゲームに組み込める層が空いている
- 競合というより**乗るべき生態系**: SillyTavern の Character Card V2 はキャラ人格の
  デファクト交換形式。duet 側に **Card→hersona 属性ブレンドのインポータ**を用意すれば、
  数万枚規模の既存カード資産とコミュニティを取り込める（Phase 4）
- 防衛線: 模倣コストが高いのは LLM 呼び出し部分ではなく、**hersona 側の決定的データ資産**
  （64属性・相性マトリクス・weight 較正・intensity）。エンジンが普及するほど
  ライブラリの堀が深くなる構造を保つ

---

## 2. プロダクト定義

### 2.1 duet が「やること」

1. **会話ランナー**: 2 つの hersona ブレンド（または プレイヤー+1 ブレンド）の交互発話を
   ターン制御。コンテキスト管理・LLM プロバイダ抽象化（BYO API キー）
2. **director**: シーン目標・話題の種・対立の種（hersona の conflicts を利用）・終了判定。
   エージェント同士が「同意ループ」に収束する既知の失敗モードを構造で防ぐ
3. **ゲーム状態機械**: 好感度スコア → hersona weight (mild/moderate/strong) への写像、
   ルート分岐（archetype 単位）、フラグ、エンディング判定、セーブ/ロード
4. **強度 QA**: 毎ターン `hersona.verify_intensity` で採点し、キャラ崩壊を検知・表示
   （オプションでリトライ）
5. **殻**: CLI（最初）と Web ノベル UI（後段）。ゲーム作品は YAML/JSON の
   コンテンツパックとして duet 上に載る

### 2.2 duet が「やらないこと」

- 属性・相性・weight 定義の所有（= hersona の責務。duet は公開 API のみ使用）
- 画像生成・音声合成の内蔵（アダプタ点だけ用意し、本体は持たない）
- 特定キャラの再現（hersona の固有名詞ガード方針を継承）
- 18禁表現（全年齢を明文化。LLM プロバイダ規約との衝突回避）

### 2.3 リポジトリ構成

```
hersona-duet/            # 新リポジトリ (MIT)
├── duet/
│   ├── runner.py        # ターン制御・履歴・プロバイダ抽象 (anthropic/openai/ollama)
│   ├── director.py      # シーン目標・対立の種・終了判定
│   ├── state.py         # 好感度→weight 写像・ルート・フラグ・セーブ
│   ├── score.py         # hersona intensity 連携 (毎ターン QA)
│   └── cli.py           # `duet run` / `duet game` 殻
├── packs/               # サンプルコンテンツパック (シーン/ヒロイン定義 YAML)
├── docs/DESIGN.md
└── pyproject.toml       # 依存: hersona>=1.2,<2
```

---

## 3. hersona 側の前提タスク（Phase 0 / duet 着手前）

| # | タスク | 内容 | 規模 |
|---|---|---|---|
| P0-1 | 配布手段の確定 | PyPI 公開（推奨。`hersona` 名の確保＋メタデータ整備）。当面は git タグ依存でも可 | 2-4h |
| P0-2 | 公開 API の明文化 | `hersona.core` のエクスポート（blend/attach・compatibility・weight・intensity・resolve_content_field）を README / IMPLEMENTATION_GUIDE に「公開 API・semver 対象」と宣言 | 2h |
| P0-3 | **好感度写像 API** | `weight_for_score(score: float) -> WeightLevel` 級の薄い関数を core/weight.py に追加（連続値 0-100 → mild/moderate/strong + ヒステリシス）。duet が要求する唯一の core 追加 | 2-3h |
| P0-4 | duet ワークストリームを ROADMAP に追記 | 「④ duet (別リポジトリ)」として参照を残す | 0.5h |

## 4. 開発フェーズ計画（週 5-10h 前提）

### Phase 1: 会話エンジン MVP — `duet run`（3-4 週）

```
duet run "tsundere kyoto_ben" "kuudere whispery" \
  --scene "放課後の図書室" --turns 10 --measure --provider anthropic
```

- [ ] runner: 2 ブレンドの注入ブロック生成（hersona API）＋交互発話＋履歴管理
- [ ] director v0: シーン文・ターン予算・「対立の種」（conflicts から自動提案）
- [ ] score: `--measure` で毎ターン intensity バッジ（pass/under/over）
- [ ] transcript 出力（Markdown / JSON）— **X 投稿用クリップの素材になる**
- 完了基準: conflict ペア 10 ターンで同意ループに陥らない確率が体感 8 割以上

### Phase 2: ゲーム状態機械 — `duet game`（4-6 週）

- [ ] state: 好感度スコア（LLM 採点 or ルールベースのハイブリッド）→ P0-3 の写像で
      weight が動的に変わる（**好感度が上がるとツンが緩む**＝最大の見せ場）
- [ ] プレイヤーモード: 片側の話者を人間入力に差し替え
- [ ] ルート/フラグ/エンディング: archetype 単位のルート、YAML 定義のフラグ条件
- [ ] セーブ/ロード（JSON）
- [ ] サンプルパック 1 本（ヒロイン 3 人: 属性ブレンドのみで定義、固有名詞なし）
- 完了基準: CLI で 1 ルート 15-30 分の通しプレイが成立する

### Phase 3: ノベル UI（4-6 週、Phase 2 と一部並行可）

- [ ] Web 殻: ブラウザ完結（BYO キーをローカル保存）。hersona の site/ と同様
      GitHub Pages 配信でホスト費ゼロ
- [ ] テキストノベル表示・選択肢・好感度メーター・weight 変化の可視化
- [ ] 立ち絵はプレースホルダ枠のみ（画像生成はアダプタ任せ、本体に持たない）

### Phase 4: 生態系接続（以降随時）

- [ ] **Character Card V2 インポータ**: 散文カード → LLM で属性ブレンド推定 → hersona
      形式に変換。SillyTavern コミュニティからの流入動線
- [ ] コンテンツパック仕様の文書化（「duet でギャルゲーを作る」チュートリアル）
- [ ] hersona 側グロース施策との連動: duet の対話ログを X エージェントの定常コンテンツに

### マイルストーン / KPI

| 時点 | マイルストーン | KPI |
|---|---|---|
| +1 ヶ月 | `duet run` 公開 + 対話ログを X 投稿開始 | 対話クリップ投稿 週 2 本 |
| +3 ヶ月 | `duet game` でサンプルパック通しプレイ | duet Star 50 / hersona への流入増 |
| +6 ヶ月 | Web ノベル UI + Card インポータ | duet Star 200 / 外部コンテンツパック 1 本 |

## 5. リスクと対策（正直版）

| リスク | 影響 | 対策 |
|---|---|---|
| エージェント同士の会話が単調・同意ループ化 | エンジンの存在意義に直撃 | director を一級モジュールに（シーン目標・対立の種・ターン予算）。conflicts データを「ドラマの燃料」として使う |
| API コスト（10 ターン×2 話者で数円〜数十円/セッション） | 普及の摩擦 | BYO キー必須・ローカル LLM (ollama) アダプタを Phase 1 から用意 |
| 恋愛コンテンツの 18 禁ドリフト | プロバイダ規約・評判 | 全年齢を README / DISCLAIMER に明文化。パック検証に NG 表現ゲート |
| 「あのキャラと恋愛したい」需要による固有名詞流入 | hersona の権利方針が崩れる | 固有名詞ガードをパック検証に組み込み（共有時のみ発動、ローカル自由 — hersona と同方針） |
| SillyTavern との比較で「機能が少ない」と言われる | ポジション誤解 | 「アプリ vs エンジン」の違いを README 冒頭で明示。V2 カードインポータで補完関係を演出 |
| 2 リポジトリ並行による開発分散（週 5-10h） | 両方停滞 | Phase 0 完了までは hersona に集中。duet 着手後は hersona を「メンテ+API 安定」モードに |

## 6. 意思決定の記録

- duet は **hersona と別リポジトリ**（名称推奨: `hersona-duet`）。理由: ①エンジンという
  独立プロダクト性 ②恋愛コンテンツのリスク隔離 ③「hersona をライブラリとして使う
  最初の外部実例」という戦略価値
- hersona core は LLM 非依存・決定的のまま維持。LLM 呼び出しは全て duet 側
- duet は `hersona>=1.2,<2` でピン留めし、公開 API のみ使用。開発期は
  `uv pip install -e ../hersona` で並行開発
