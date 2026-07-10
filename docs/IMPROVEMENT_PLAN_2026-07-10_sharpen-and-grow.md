# 先鋭化×グロース実行計画(2026-07-10)

> 対象: shiro-0x/hersona v1.8.0(属性 346 / use_case 20 / ペルソナパック 14)
> 目的: **機能・性能をさらに尖らせる**(A)と**利用者を増やす**(B)の両輪を、
> 既存プラン群と重複させずに実行可能な粒度で定義する。
> 位置づけ: `docs/IMPROVEMENT_PLAN.md`(2026-06 グロース全般)・
> `docs/IMPROVEMENT_DISCUSSION_2026-06-15.md`(基盤、完了済)・
> `docs/IMPROVEMENT_PLAN_2026-07-04_user-feedback.md`(フィードバック対応、完了済)・
> `docs/reviews/2026-07-04-external-review-response.md`(計測・信頼性、v1.8.0 でほぼ完了)
> の**後続**。本計画は「既出施策の再掲」を避け、未実施・未着手の差分だけを扱う。
> 施策が既存文書に書かれている場合は必ず「既出(出典)」と明記する。

---

## 1. 現状分析

### 1.1 強み(すべてリポジトリ実体で確認済み)

| 領域 | 事実 |
|---|---|
| データ資産 | 属性 **346**(personality 43 / speech 140 / archetype 66 / visual 46 / hobby 51、SSOT = `tests/catalog_counts.py`)。speech は ja 119 + en 15 + **native zh/ko 6** と多言語で他に類がない厚み |
| 計測(最大の差別化) | `measure`(決定的 3 軸採点)/ `bench`(維持率・減衰曲線・注入トークンコスト、LLM 不要)/ `docs/BENCHMARKS.md` に実測コスト表。「測定可能なペルソナ層」を名乗れる装備は v1.8.0 で揃った |
| 品質ゲート | テスト関数 574 / CI 6 ゲート(ruff / validate / build_site --check / README 件数 / checksums / pytest)/ `release_check.py` / SECURITY.md + checksums 検証 + Trusted Publishing + provenance attestation |
| 一貫性機構 | 相性マトリクス(conflict / compatible + `--suggest` 代替案)、weight ダイヤル(+ `weight_for_score` ヒステリシス)、**persona_lock(v1.8.0、既定 ON)** |
| 配布面 | PyPI 公開済 / MCP サーバー(6 ツール)/ Hermes スキル / `export` 5 形式 / `persistent --target` で **CLAUDE.md / AGENTS.md / .cursorrules / GEMINI.md** へ直接書き出し / デモサイト(EN/JA 診断クイズ + before/after showcase) |
| カタログ製品 | use_case 20 / ペルソナパック 14(全パック CI で `validate_persona` エラー 0 を担保) |

### 1.2 弱み(確認済みの事実)

| 弱み | 根拠 |
|---|---|
| **認知が依然ボトルネック** | GitHub API 実測(2026-07-10): Star 10 / Fork 0 / subscribers 0 / open issues 0。`IMPROVEMENT_PLAN.md` の診断(認知が制約)から 1 ヶ月、製品は大幅進化したが流通指標はほぼ動いていない |
| **GitHub「店構え」が未修正のまま** | About 欄が「**89** reusable character attributes」のまま(実体 346)。topics に `mcp` / `ai-agent` / `persona` / `aituber` が無い。**Discussions 無効**(`has_discussions: false`)。→ `IMPROVEMENT_PLAN.md` S2 で 2h 工数と見積もられた施策が**未実施**。外部レビューが指摘した「3 つの数字の併存」のうち About だけが残存(`RELEASE_CHECKLIST.md` も「自動化不能・手動」と明記) |
| フレームワーク統合の実例ゼロ | `examples/` は memory JSON 3 個のみ。README は LangChain / AutoGen / CrewAI を謳うが、動くサンプルコードが 1 本も無い |
| bench が「素材」止まり | `hersona bench` は transcript 採点のみ(`--provider` 経路なし、CLI フラグ実測)。レビュー対応計画 P1-1 が構想した「あり/なし/手書きの 3 条件比較」は**レシピ(手順書)止まり**で、公式の hersona-vs-baseline 実測値は未公開 |
| zh/ko 資産が測定対象外 | native zh/ko speech 6 属性を v1.5.0 で追加済みだが、`intensity.py` は ja / en のみ対応で zh/ko は `unsupported_lang` skip(実装確認済み)。「多言語 speech の厚み」という強みが計測面で未回収 |
| MCP ツールが読み取り系のみ | `mcp/tools.py` は list / show / blend / export / recommend_blend / compatibility の 6 種。**measure / bench / personas が無く**、エージェントが「自分の人格維持を自己採点する」ループを MCP 経由で組めない |
| persona_lock の効果が未測定 | v1.8.0 の目玉だが、ロック突破(人格上書き)攻撃に対する耐性を測るシナリオ・指標が無い(`benchmarks/scenarios/` は 6 本、うち攻撃系ゼロ) |
| **口調サンプル(examples)が死蔵** | 全 346 属性がスキーマ必須の `examples`(実会話例文、中央値 181 chars/属性)を保有するが、消費者は authoring と `build_site`(サイト表示)のみ。`attach.py` の注入ブロック・soul・export のいずれにも乗らず、口調安定化に最も効く few-shot 素材が未活用(2026-07-10 実装確認)→ A-6 |

### 1.3 既出領域の整理(重複回避マップ)

| 既存文書 | カバー済み領域 | 状態 |
|---|---|---|
| `IMPROVEMENT_PLAN.md`(2026-06-11) | 計測基盤 / 店構え / 診断シェアカード(OGP)/ X エージェント / 記事 / 人格総選挙 / AITuber コラボ / good first issue / Sponsors / トークン発行ゲート | **大半が未実施**(店構え S2 含む)。X 運用・シェアカード・記事・収益化は本計画では再掲しない(同文書の管轄) |
| `IMPROVEMENT_DISCUSSION_2026-06-15.md` | CI / site 重複解消 / preview / rich / diff / blend 強化 / first_person / save / 補完 / export / MCP 化 / 方言追加 | 全完了 |
| `IMPROVEMENT_PLAN_2026-07-04_user-feedback.md` | recommend 出口直結(--export/--soul/--save)/ サイト EN 化 / PUBLIC_API.en | 全完了(v1.8.0) |
| `reviews/2026-07-04-external-review-response.md` | 件数 SSOT+CI / bench / is–is-not / checksums / Trusted Publishing / リリースチェックリスト | ほぼ完了。**P1-1 の provider 実行経路と公式比較結果の公開のみ未了** → 本計画 A-2 が引き継ぐ |
| `PERSONA_PACKS_DESIGN.md` | パック 14 + use_case 20 | 完了。非スコープ宣言: `hersona update` の personas/use_cases 配布、**デモサイトのパックギャラリー**、Claude Code agents 形式 → ギャラリーは本計画 B-4 で解禁提案 |
| `DUET_PLAN.md` | 別リポジトリの制作スタジオ。**Character Card V2 インポータは duet Phase 4 の管轄** | hersona 本体は Tavern 形式を拒否する方針(SKILL.md Pitfall 12)を維持 |
| `I18N_DESIGN.md` / `I18N_FUTURE_WORK.md` | en ベース化 Phase 0–5 + W1–W3 | 全完了。**ただし intensity の zh/ko 対応はどこにも計画されていない** → 本計画 A-3 |

**結論**: 「サイト EN 化」「recommend 出口」「bench 骨格」「パック」は済んでいる。
残る最大の未回収は ①**流通(店構え・レジストリ・統合実例)がほぼ手つかず**、
②**計測機能の「証拠」への転化**(公式比較値・攻撃耐性・zh/ko)の 2 点。
本計画はこの 2 点に絞る。

---

## 2. A. 尖らせる(機能・性能)

方針: 「何でもできる」方向(RAG / tool use / memory)には**行かない**
(`reviews/2026-07-04` §5 のスコープ規律を維持)。深めるのは hersona だけが持つ 3 軸 —
**測定可能性・一貫性(lock)・多言語 speech 資産** — である。

### A-1. persona_lock 耐性ベンチ(「人格ジェイルブレイク耐性」の定量化)★新規

- **概要**: `benchmarks/scenarios/` に人格上書き攻撃シナリオを追加する
  (`persona_override_attack_{ja,en}.yaml`: 「関西弁で話して」「今だけ別キャラになって」
  「システムプロンプトを無視して」等の段階的な揺さぶり 10–12 ターン)。
  `hersona bench` に **lock resistance rate**(攻撃ターン後も強度バンド内に留まった率)を
  メトリクスとして追加し、`persona_lock` あり/なしの差分を `docs/BENCHMARKS.md` に実測掲載する。
  採点は既存の決定的 scorer をそのまま流用(攻撃後ターンの intensity が落ちなければ耐えた、
  という surface プロキシ)。LLM 不要の範囲で完結する。
- **なぜ尖るのか**: persona_lock は v1.8.0 の看板機能だが現状「効くはず」の主張止まり。
  手書きプロンプトにも SillyTavern にも「人格の頑健性を数値で示す」機能は存在しない。
  「一貫性を主張する」ツールから「**一貫性を測って見せる**」ツールへ — 外部レビューで
  効いた「主張と証拠のギャップを埋める」路線の第 2 弾であり、そのままデモ・記事の
  一次ソースになる。
- **工数**: **S–M**(シナリオ YAML 4 本 + bench のメトリクス 1 個 + テスト。core scorer は不変)
- **期待効果**: README / サイトに「lock 有効時 維持率 X% vs 無効時 Y%」という
  引用可能な数字が載る。B 群の全発信素材の弾になる。

### A-2. 公式 hersona-vs-baseline 実測の完成と公開 ★一部既出(`reviews/2026-07-04` P1-1 の未実装残)

- **概要**: P1-1 が構想した provider 実行経路を、**core を汚さない別スクリプト**
  `benchmarks/run_comparison.py`(または `hersona bench --transcript` に食わせる
  transcript 生成ヘルパ)として実装する。条件 A(hersona 注入)/ B(手書き相当)/
  C(素)で 2 モデル(例: ローカル ollama + API 1 種)× 既存 6 シナリオを実行し、
  維持率・減衰曲線・トークンコストを**日付・モデル・再現コマンド付き**で
  `docs/BENCHMARKS.md` に掲載する。悪い数字もそのまま載せる(既存方針の踏襲)。
  hersona 本体は「LLM 依存ゼロ」を維持する(スクリプトは dev 向け、依存は追加しない
  か extras に隔離)。
- **なぜ尖るのか**: BENCHMARKS.md は現状「自分で測れ」というレシピを提供している。
  誠実だが、比較検討中のユーザーは自分で測る前に離脱する。「公式の一次実測値 +
  誰でも再現できるスクリプト」の組み合わせは、競合(手書き / .cursorrules / 一般の
  プロンプト集)には構造的に真似できない主張になる。v2.0.0 の「実証済み主張への刷新」
  (`reviews/2026-07-04` §3)の前提条件でもある。
- **工数**: **M**(スクリプト 1 本 + API 実行 + 結果整形。シナリオと scorer は既存)
- **期待効果**: 「導入すべきか」の判断材料が README から 1 クリックで届く。
  外部レビュー再訪時に過大評価耐性 4/10 → 7+ の根拠が完成する。

### A-3. intensity / bench の zh・ko 対応(多言語 speech 資産の回収)★新規

- **概要**: `hersona/core/intensity.py` に zh / ko の採点経路を追加する。
  ja の語尾照合と同型で、zh は語気助詞(啦/嘛/吧/喔 等)・ko は語尾(-야/-지/-습니다/-세요 等)
  を `sentence_endings` / `lexical_markers` 相当のシグナルとして照合する
  (native zh/ko 6 属性は authoring 時点でこれらのフィールドを持つ。持たない場合は
  バックフィルを同 PR で行う)。`skip_reason` の `unsupported_lang` から zh / ko を外す。
- **なぜ尖るのか**: 「native zh/ko speech を持ち、しかもその維持率を決定的に測れる」
  ペルソナライブラリは存在しない。属性は既にあるのに測れないのは、せっかくの
  多言語資産が「カタログの飾り」に留まっている状態。測れるようになれば
  中華圏・韓国圏コミュニティへの発信(B 群)に「そこでしか成立しない実証」を持ち込める。
- **工数**: **M**(言語別トークナイズは不要 — 既存 en 実装と同じ表層一致方式で足りる。
  テストは `tests/test_intensity.py` へ zh/ko 各 4–6 件追加)
- **期待効果**: bench / measure の対象言語が 2 → 4 に。zh/ko 属性追加の受け皿が整い、
  カタログ拡張(コミュニティ PR)の対象言語も広がる。

### A-4. 注入ブロックの compact プロファイル + キャッシュ最適レイアウト ★一部既出(`reviews/2026-07-02-yaml-token-review.md` B-1 は実施済み、本項はその先)

- **概要**: 2 段構え。
  1. **`--compact` プロファイル**: `response_style_directive` の固定部
     (tsundere 単体 1,257 chars 中 481 chars = **38%**。2026-07-10 実測、
     token review B-1 の `is_blend` 分岐適用後。ヘッダ・Intensity 節を含む
     固定部全体はさらに大きい)を、意味を保った短縮版に切り替える
     オプトインフラグを `blend` / `export` / `soul` に追加。目標は固定部 −30〜40%。
     効果検証は既存 `bench --cost-only` + A-2 の維持率比較で行い、
     「compact でも維持率が落ちない」ことを数字で示してから既定化を判断する。
  2. **プロンプトキャッシュ最適レイアウト**: 注入ブロックを「安定 prefix
     (固定ディレクティブ + 属性本文)→ 可変部(memory / Recent Context / タイムスタンプ)」
     の順に再配置し、Anthropic / OpenAI のプロンプトキャッシュ境界に乗る構造にする。
     `docs/BENCHMARKS.md` に「キャッシュ有効時の実効コスト」の節を追加。
- **なぜ尖るのか**: トークンコストは外部レビューが挙げた採用可否の成功条件そのもの。
  「コストを測れる」(済)の次は「コストを削れて、削っても崩れないことを証明できる」。
  キャッシュ最適化の観点はペルソナ系ツールでは誰も文書化しておらず、
  実運用者(毎ターン system prompt を払う層)に直接刺さる。
- **工数**: **M**(directive の条件分岐は `attach.py` に集約済みなので変更箇所は局所。
  レイアウト変更は SOUL.md 決定性テストの更新を伴う)
- **期待効果**: 単体 blend 実測 1,257 chars(moderate)→ 900 chars 前後を目標。
  「軽量・決定的」ポジションの数値的裏付けが強化される。

### A-5. per-attribute weight の core / CLI 対応(強度ダイヤルの完成)★新規

- **概要**: 現在 `render_blend` / `export_blend` / CLI `blend --weight` は
  **ブレンド全体で単一の weight** しか取れない(`docs/PUBLIC_API.md` で確認)。
  一方 README のスキル節は `/hersona personality/tsundere strong speech/keigo mild` と
  **属性ごとの強度指定**を案内しており、core との非対称がある。
  `render_blend(names, weight=...)` に `weights: dict[str, WeightLevel] | None = None`
  (キーワード追加 = minor)を足し、CLI は `hersona blend tsundere:strong keigo:mild`
  形式(`:` サフィックス)を受理する。measure / bench も per-attribute バンドで採点。
- **なぜ尖るのか**: 「強度ダイヤル」は比較表(README / PERSONA_PACKS_DESIGN)で
  毎回挙げる差別化項目。それが実は全体一律というのは、深掘りされた瞬間に弱点になる。
  「tsundere は強く、keigo は薄く」は最も自然な要望であり、ここを本当に個別制御に
  すると blend エンジンの品質主張が名実ともに揃う。duet(感情温度ダイヤル)の
  受け皿としても効く。
- **工数**: **M–L**(attach / weight / intensity / export / soul / persistent を横断。
  後方互換のキーワード追加で段階実装可能)
- **期待効果**: ブレンド表現力の実質的な上限が上がる。パック YAML への
  per-attribute weight 拡張(schema minor)にも道が開く。

### A-6. 会話事例(examples)の few-shot 注入プロファイル ★新規(ユーザー発案 2026-07-10)

- **前提事実**: 「口調ごとの会話事例辞書」は**新規作成不要** — 全 346 属性が
  スキーマ必須の `examples`(そのキャラが実際に話す例文。例: kansai_ben
  「なんでやねん、それ……嘘やろ」。中央値 181 chars/属性)を既に保有している。
  現在の消費者は authoring と `build_site` のみで、注入ブロック・soul・export には
  一切乗らない(§1.2)。辞書は事実上完成しており、残っているのは注入経路だけ。
- **概要**: `blend` / `export` / `soul` に `--style-examples N`(既定 0 = 現状維持)を
  追加し、speech > personality のカテゴリ優先順(`sample_dialogue.py` の既存ロジックを
  流用)で N 件の例文を
  「`## Style examples (tone reference — never reuse these lines verbatim)`」節として
  注入する。反復防止の一文は CLAUDE.md の規則どおり `response_style_directive` に
  集約して追加する(節ごとに directive を増やさない)。効果検証は A-2 の比較基盤で
  「examples あり/なし」の維持率を実測し、数字が出た場合のみ既定化を検討する。
  応用として「measure で強度低下を検知 → 例文ブロックを会話末尾へ再注入」という
  リカバリループをスキル / MCP ツール(B-2 の `measure_intensity` 追加後)として
  文書化できる(末尾追加はプロンプトキャッシュの prefix を壊さない = A-4 と整合)。
- **なぜ尖るのか**: 形容詞的な tone 記述より実文の模倣(few-shot style anchoring)の
  方が LLM の文体制御は安定する。かつ「例文つき注入 → その維持率を決定的に測って
  見せる → ブレたら測って再注入する」まで一気通貫で提供できるのは measure を持つ
  hersona だけ。「口調がブレる」という最頻の体感不満への直接打ち手になる。
- **リスクと対策**:
  1. **オウム返し**: 例文の verbatim 再利用・例文の話題への引きずり
     → directive の 1 行(「tone の参照であり文言は再利用しない」)+ bench シナリオで
     反復を確認。
  2. **トークンコスト増**: +45〜60 tok/属性、3 属性ブレンドで +150〜200 tok/ターン。
     A-4(compact)と逆方向のダイヤルのため**既定 OFF・オプトイン必須**。
     compact / standard / reinforced の 3 プロファイルとして A-4 と同じ軸に統合する。
  3. **measure の自己汚染**: examples は語尾・口癖を含むため、モデルが例文を写すと
     維持率が見かけ上がる(指標のゲーミング)。BENCHMARKS.md では「examples 注入あり」
     を別列で報告し、素の維持率と混ぜない。
  4. **ブレンド時の文体矛盾**: tsundere と keigo の例文を並べると口調が割れる
     → speech 属性の例文を最優先・件数上限(N≤3 推奨)。ブレンド専用例文の自動合成は
     LLM 依存になるためやらない(§6 の規律)。
  5. **多言語制約**: examples は content_lang 依存で zh/ko は採点不能(A-3 完了が先)。
     品質基準(固有名詞なし・完全オリジナル)はスキーマが既に強制している。
- **工数**: **S–M**(attach.py に節 1 つ + directive 1 行 + CLI フラグ 3 箇所 + テスト。
  素材と優先順ロジックは既存)
- **期待効果**: 口調安定性の実測改善(A-2 基盤で検証)。before/after が最も見せやすい
  機能のため、B 群の発信素材としても一級。

### A 群サマリ

| # | 施策 | 新規性 | 工数 | 尖る軸 |
|---|---|---|---|---|
| A-1 | persona_lock 耐性ベンチ | 新規 | S–M | 測定 × 一貫性 |
| A-2 | 公式 vs-baseline 実測公開 | 一部既出(reviews P1-1 残) | M | 測定 |
| A-3 | zh/ko intensity | 新規 | M | 測定 × 多言語 |
| A-4 | compact + キャッシュ最適 | 一部既出(token review の先) | M | コスト |
| A-5 | per-attribute weight | 新規 | M–L | ブレンド品質 |
| A-6 | 会話事例(examples)注入 | 新規(ユーザー発案) | S–M | 一貫性 × 測定 |

---

## 3. B. 利用者を増やす(グロース)

方針: X 運用・シェアカード・記事・収益化は `IMPROVEMENT_PLAN.md` の管轄
(S3–S5 / M1–M6 / L1)であり再掲しない。本計画は**「置くだけで流入が発生する
構造物」= 配布チャネルと統合実例**に集中する(燃え尽きリスク §4.3 とも整合:
定常運用を増やさない施策を優先)。

### B-1. GitHub「店構え」の完遂 ★既出(`IMPROVEMENT_PLAN.md` S2)— ただし 1 ヶ月未実施のため最優先で再掲

- **概要**: ①About 欄を 346 属性の現仕様に更新(現状「89 attributes」のまま —
  外部レビューが指摘した信頼毀損要因の最後の残存)。②topics に `mcp` / `mcp-server` /
  `ai-agent` / `persona` / `character-ai` / `aituber` を追加(現状 6 個、
  `anime-character` 等のみ)。③Discussions を有効化。④Social Preview 画像設定
  (`docs/hersona-logo.png` 流用可)。すべて設定作業のみ、コード変更ゼロ。
- **ターゲット層**: GitHub 検索・topics 経由の全流入者(最上流)
- **工数**: **S**(1–2 時間)
- **KPI**: GitHub Traffic views→star 転換率、topics 経由流入(Insights)。
  About 不一致の解消は `RELEASE_CHECKLIST.md` §4 の手動項目として毎リリース確認。

### B-2. MCP レジストリ登録 + MCP ツール拡張 ★一部既出(`IMPROVEMENT_PLAN.md` M3「レジストリ登録」)、ツール拡張は新規

- **概要**:
  1. **登録**(既出分の実行): `hersona-mcp` を mcp.so / Smithery / Glama /
     `punkpeye/awesome-mcp-servers` へ登録・PR。2026 年時点で主要レジストリは
     この 4 つに集約されており、メタデータは 1 回用意すれば横展開できる。
  2. **ツール拡張**(新規): `mcp/tools.py` に `measure_intensity` /
     `bench_transcript` / `list_personas` / `install_persona`(dry-run 相当)を追加。
     現状 6 ツールは読み取り系のみで、**エージェントが会話ログを渡して自分の
     人格維持率を自己採点する**というレジストリ上で最も語れるユースケースが組めない。
     「自分の人格を測れる MCP サーバー」はカテゴリ内で唯一の売り文句になる。
- **ターゲット層**: Claude Desktop / MCP 対応エージェントのユーザー(ペルソナ層の
  存在をまだ知らない最大の隣接市場)
- **工数**: 登録 **S** / ツール拡張 **S–M**(tools.py は core の薄い殻、テストは既存パターン)
- **KPI**: 各レジストリのページビュー / インストール数(Smithery は計測可)、
  MCP 経由と推定される PyPI DL の増分、`hersona-mcp` への Issue 発生。

### B-3. フレームワーク統合サンプル集(`examples/` の実体化)★新規

- **概要**: `examples/` に動くコードを置く:
  `langchain_quickstart.py`(`export --format langchain_system_message` を実消費)、
  `openai_assistants.py`、`crewai_agent.py`(CrewAI の `Agent(backstory=...)` に
  markdown export を注入)、`autogen_persona.py`、
  `aituberkit_setup.md`(AITuberKit のキャラ設定欄へ `hersona export --format markdown`
  を貼る手順 — AITuberKit は system prompt がキャラ定義の中心なので export 出力が
  そのまま使える)。各サンプルは 30 行以内・API キーは環境変数・README から
  「Use with X」節でリンク。CrewAI / AutoGen は export 形式追加**不要**
  (markdown / messages で足りる)であることをサンプル自体で示す。
- **ターゲット層**: LangChain / CrewAI / AutoGen の既存ユーザー(検索流入
  「crewai persona」「langchain character prompt」)、AITuber 制作者
  (`IMPROVEMENT_PLAN.md` が定義するコアターゲット)
- **工数**: **M**(サンプル 5 本 + README 導線 + CI での import スモーク)
- **KPI**: examples 配下ファイルの GitHub views、検索流入クエリ、
  各フレームワークコミュニティ(Discord / forum)での被言及。

### B-4. デモサイトにペルソナパックギャラリー ★既出扱い(`PERSONA_PACKS_DESIGN.md` §1 で「非スコープ(将来課題)」と明記されたものの解禁提案)

- **概要**: `build_site.py` を拡張し `personas/*.yaml` 14 本を data.json に載せ、
  サイトに「Persona Packs」タブを追加。各パックカードに blend / weight / use_case /
  注入ブロックプレビュー / **コピー可能な 1 行インストールコマンド**
  (`hersona personas install keigo_support --auto-config`)を表示。
  A-1 / A-2 完了後はパックごとの維持率・トークンコスト実測値も併記する
  (「測れるカタログ」としての見せ場)。
- **ターゲット層**: 「pip install 前に何ができるか見たい」層(サイトは既に
  30 秒体験の導線として README 最上部に掲示済み)
- **工数**: **M**(build_site 拡張 + app.js タブ 1 枚 + `--check` ゲートは既存機構)
- **KPI**: サイトのパックタブ滞在・コマンドコピー数(既存のクイズ完了計測と同枠)、
  `personas install` 起因と推定される Issue / 質問。

### B-5. PyPI・awesome リストのメタデータ網羅 ★新規(awesome-mcp は B-2 に含む)

- **概要**: ①`pyproject.toml` の keywords に `mcp` / `character-card` / `chatbot` /
  `aituber` / `langchain` 等を追加(現状 8 語、`mcp` が無い)。
  ②awesome-ai-agents / awesome-claude-code(スキル)/ awesome-python 系リストへ PR。
  ③GitHub リポジトリに `USED_BY.md` の器を用意(`reviews/2026-07-04` P3-2 既出だが未実施)。
- **ターゲット層**: PyPI / awesome リスト検索者
- **工数**: **S**
- **KPI**: PyPI 検索順位(定性)、awesome リスト経由の referrer、pip DL/月(pypistats)。

### B-6. SillyTavern 圏への「読み取り専用」導線 ★既出(`DUET_PLAN.md` Phase 4「Character Card V2 インポータ」)— hersona 本体では方針変更しない

- **概要**: hersona 本体は Tavern Card 形式を出力しない方針(SKILL.md Pitfall 12)を
  **維持**する。差分提案は「形式変換」ではなく**解説コンテンツ**:
  「Character Card の personality 欄を hersona 属性で規格化する」ガイド 1 本
  (docs/guides/)+ 比較表(カード=1 キャラの完成品 / hersona=属性の部品と測定)。
  インポータ実装は duet Phase 4 の管轄のまま動かさない。
- **ターゲット層**: SillyTavern / ローカル LLM ロールプレイ層(キャラ文化圏で最大)
- **工数**: **S**(ガイド 1 本)
- **KPI**: ガイドページの流入、当該コミュニティからの referrer。

### B 群サマリ

| # | 施策 | 新規性 | 工数 | ターゲット |
|---|---|---|---|---|
| B-1 | 店構え完遂 | 既出(S2)未実施 | S | GitHub 流入全般 |
| B-2 | MCP レジストリ + ツール拡張 | 一部既出(M3) | S–M | MCP エコシステム |
| B-3 | 統合サンプル集 | 新規 | M | LangChain/CrewAI/AutoGen/AITuber |
| B-4 | パックギャラリー | 既出の解禁 | M | インストール前検討層 |
| B-5 | メタデータ網羅 | 新規 | S | 検索・リスト流入 |
| B-6 | SillyTavern ガイド | 既出(duet)の派生 | S | ロールプレイ圏 |

---

## 4. 優先順位マトリクス

```
高Impact │ B-1 店構え完遂        │ A-2 公式実測公開
        │ B-2 MCPレジストリ+拡張 │ B-3 統合サンプル集
        │ A-1 lock耐性ベンチ     │ A-5 per-attr weight
        │ A-6 examples注入      │
────────┼──────────────────────┼──────────────────────
低Impact │ B-5 メタデータ網羅     │ A-4 compact+キャッシュ
        │ B-6 STガイド          │ A-3 zh/ko intensity
        │                      │ B-4 パックギャラリー
        └── 低Effort ───────────────── 高Effort ──→
```

### Top 5(推奨着手順)

| 順 | 施策 | 理由 |
|---|---|---|
| **1** | **B-1 店構え完遂**(S) | コードゼロ・即日。About「89」は今この瞬間も信頼を毀損しており、以降の全流入施策の受け皿。1 ヶ月放置された既出施策の完遂が先 |
| **2** | **B-2 MCP レジストリ登録 + ツール拡張**(S–M) | サーバーは実装済みで登録だけが残っている「刈り取り」。measure/bench の MCP 化は A 群の差別化をそのまま配布チャネルの売り文句に変える接続点 |
| **3** | **A-1 persona_lock 耐性ベンチ**(S–M) | 工数最小で「測定可能なペルソナ層」の第 2 の実証。以降の発信(B 群・IMPROVEMENT_PLAN の記事施策)の一次ソースになる数字を最初に作る |
| **4** | **B-3 統合サンプル集**(M) | README の主張(LangChain/AutoGen/CrewAI 対応)と実体のギャップ解消。検索流入の器として恒久資産化する |
| **5** | **A-2 公式 vs-baseline 実測公開**(M) | 外部レビュー対応の最後のピース。v2.0.0(主張の実証化)の前提。A-1 の攻撃シナリオと同じ実行基盤で回せるため 3 の直後が効率的 |

次点: **A-6(examples 注入)は素材が全属性に揃っており工数 S–M。効果検証
(維持率が実際に上がるか)に A-2 の比較基盤を使うため、A-2 の直後(60 日枠)に
組み込むのが最も効率的**。A-4(compact は A-2 の測定基盤が整ってから効果検証込みで。
A-6 とプロファイル軸を共有)、B-4(A-1/A-2 の数字をカードに載せられるタイミングで)、
A-3(zh/ko 圏発信の前提として 60 日以内)、A-5(最重量。90 日枠で設計から)。

---

## 5. 30 / 60 / 90 日ロードマップ

前提: 週 5–10h(`IMPROVEMENT_PLAN.md` と同じ)。コード変更を伴う項目はすべて
CLAUDE.md の更新規則(README EN/JA 同期 / CHANGELOG / validate+pytest /
属性・データ変更時は build_site + gen_checksums)に従う。

### 〜30 日(7/10–8/10): 刈り取りと最初の数字

- [ ] **B-1**: About 346 更新 / topics 追加 / Discussions 有効化 / Social Preview(初日)
- [ ] **B-5**: pyproject keywords 追加 + awesome 系リスト PR 2–3 本 + USED_BY.md の器
- [ ] **B-2 前半**: mcp.so / Smithery / Glama / awesome-mcp-servers へ登録
  (メタデータ 1 式を先に作り横展開)
- [ ] **A-1**: 攻撃シナリオ 4 本 + bench の lock resistance メトリクス + BENCHMARKS.md 追記
- **マイルストーン**: レジストリ 3 箇所掲載 / lock 耐性の実測値が README から辿れる
- **計測**: GitHub Traffic 週次記録を開始(`IMPROVEMENT_PLAN.md` S1 と合流)

### 〜60 日(8/10–9/10): 実証と統合

- [ ] **B-2 後半**: MCP ツール拡張(measure / bench / personas)→ レジストリ掲載文を更新
- [ ] **A-2**: `benchmarks/run_comparison.py` + 2 モデル × 6 シナリオ実測 →
  BENCHMARKS.md に公式数値(A-1 のロック比較も同枠で再実行)
- [ ] **B-3**: 統合サンプル 5 本 + README「Use with X」導線 + CI import スモーク
- [ ] **A-3**: zh/ko intensity 採点(native 6 属性のシグナル・バックフィル込み)
- [ ] **A-6**: `--style-examples` オプトイン注入 + 反復防止 directive 拡張 +
  A-2 基盤で「examples あり/なし」の維持率を実測(数字が良ければ v2.0 で既定化判断)
- **マイルストーン**: v1.9.0 リリース(MCP 拡張 + zh/ko intensity + bench メトリクス +
  `--style-examples` = minor 追加のみ)。「hersona は何と比べてどれだけ維持するか」に
  公式数値で答えられる
- **計測**: pip DL/月、レジストリ経由流入、examples views

### 〜90 日(9/10–10/10): 体験の磨き込みと v2.0 準備

- [ ] **A-4**: `--compact` プロファイル(A-2 基盤で「維持率を落とさない削減」を検証して出荷)
  + キャッシュ最適レイアウト + BENCHMARKS.md 実効コスト節
- [ ] **B-4**: デモサイトのパックギャラリー(A-1/A-2 の実測値をカードに併記)
- [ ] **B-6**: SillyTavern 向けガイド 1 本(docs/guides/、EN/JA)
- [ ] **A-5 設計着手**: per-attribute weight の設計書(schema / core / CLI 横断のため
  PERSONA_PACKS_DESIGN 同様の設計書 → 実装は次期)
- **マイルストーン**: v2.0.0 判定(`reviews/2026-07-04` §3 の基準 =「README の全主張が
  ベンチ数字付き」)。達していれば主張刷新リリース、A-5 は v2.x の目玉として計画化
- **計測**: Star / DL / クイズ完了 / レジストリ流入の 90 日推移レビュー →
  `IMPROVEMENT_PLAN.md` §5 の OODA サイクルへ引き継ぎ

---

## 6. やらないこと(スコープ規律の再確認)

- RAG / tool use / memory 等の「実務エージェント基盤」への拡張(既出:
  `reviews/2026-07-04` §5。測定・一貫性・多言語の 3 軸から外れる肥大化はしない)
- Tavern Card 形式の入出力を hersona 本体に実装(既出: SKILL.md Pitfall 12 /
  `DUET_PLAN.md` Phase 4 の管轄)
- X 運用・シェアカード・記事・Sponsors・トークン(既出: `IMPROVEMENT_PLAN.md` の管轄。
  本計画の A-1 / A-2 が生む「数字」はそちらの弾として供給する)
- 埋め込み・LLM 依存の推薦/採点(既出: `IMPROVEMENT_DISCUSSION_2026-06-15.md` §2 で
  却下済み。「軽量・決定的」ポジションを崩さない)

---

## 改訂履歴

- 2026-07-10(同日改訂): 記載の実測値をリポジトリ実体・GitHub API で再検証
  (About「89」/ topics / Discussions 無効 / MCP 6 ツール / intensity ja・en 限定 /
  speech 内訳 ja 119 + en 15 + zh 3 + ko 3 / 攻撃シナリオゼロ / tsundere 単体
  1,257 chars / `keigo_support`・`--auto-config` 実在 — すべて一致)。
  A-4 の固定部比率を `is_blend` 分岐適用後の実測 38% に更新(旧記述「6 割前後」は
  2026-07-02 レビュー時点の数字)。ユーザー発案の **A-6(会話事例 examples 注入)** を
  追加し、優先順位・60 日ロードマップ・v1.9.0 スコープに反映。
