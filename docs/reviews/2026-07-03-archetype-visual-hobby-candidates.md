# 追加候補: archetype / visual / hobby (2026-07-03)

現状: **archetype 9 / visual 5 / hobby 5**。ギャップ埋めの汎用属性を選定した。
すべて **固有名詞・特定作品を含まない**(CC0 テンプレート方針)。既存の
personality / speech / archetype と照合済み。

各候補の凡例:
- **◎ 第1弾** … まず入れたい定番(バランス重視の推奨セット)
- **○ 追加候補** … 第2弾以降 or 好みで採用

> 注: archetype は「役割・関係性の軸」。speech 側に近い口調
> (`oujo` / `butler` / `sensei` / `onee_san` / `miko`)があるものは、既存の
> `shrine_maiden`(archetype)↔`miko`(speech)と同じく **立場 vs 口調** で
> 別軸として成立する。重複ではない。

---

## archetype 候補(現 9 → 提案)

| | name | 表示名 | コンセプト | core_traits 案 | compatible / conflicts の当たり |
|---|---|---|---|---|---|
| ◎ | `senpai` | 先輩 | 頼れる年上の先輩。面倒見と余裕、後輩を導く立場 | 面倒見が良い / 余裕がある / さりげなく気にかける / 頼られると張り切る | compat: kouhai, mentor, protective / conflict: hikikomori |
| ◎ | `kouhai` | 後輩 | 慕う後輩。初々しさと憧れ、素直な甘え | 初々しい / 憧れを向ける / 素直に頼る / 一生懸命 | compat: senpai, puppyish / conflict: hautaine |
| ◎ | `ojou_sama` | お嬢様・令嬢 | 良家の令嬢。気高く世間知らず、育ちの良さ(口調でなく立場) | 気高い / 世間知らず / 誇り高い / 施しに慣れている | compat: himedere, shrine_maiden / conflict: hikikomori, delinquent |
| ◎ | `student_council_president` | 生徒会長 | 責任感の強いリーダー。規律と信頼、皆をまとめる | 責任感が強い / 規律を重んじる / 皆をまとめる / 弱音を見せにくい | compat: diligent, serious, mentor / conflict: delinquent, laid_back |
| ◎ | `detective` | 探偵 | 観察と推理の人。細部を見逃さず真相を追う | 観察眼が鋭い / 推理を組み立てる / 細部を見逃さない / 冷静 | compat: intellectual, mysterious / conflict: airhead |
| ○ | `butler` | 執事 | 忠実で有能な従者。慇懃・献身、主を第一に | 忠実 / 有能 / 慇懃 / 主を第一に置く | compat: maid, mentor / conflict: delinquent(speech に `butler` 口調あり) |
| ○ | `maid` | メイド | 気配りの使用人。献身と控えめな気遣い | 献身的 / 気配り上手 / 控えめ / 主人思い | compat: butler, protective / conflict: hautaine |
| ○ | `delinquent` | 不良・ヤンキー | 粗野な外見の裏に情。突っ張るが仲間思い(立場。speech の `yankee` は口調) | 突っ張る / 情に厚い / 群れる / 実は面倒見が良い | compat: rival, hot_blooded / conflict: ojou_sama, student_council_president |
| ○ | `knight` | 騎士 | 忠誠と守護。誓いを重んじ、守るべきもののために立つ | 忠誠心 / 守護の誓い / 実直 / 自己犠牲的 | compat: protective, heroine / conflict: scheming |
| ○ | `villain` | 悪役・敵役 | 物語の敵役。信念ある対立軸(speech の `villainess` は口調) | 信念ある対立 / 余裕の態度 / 目的のため手段を選ばない / 美学がある | compat: rival, mysterious / conflict: heroine |

**第1弾推奨(archetype +5)**: senpai, kouhai, ojou_sama, student_council_president, detective
→ 9 → 14

---

## visual 候補(現 5 → 提案)

visual は「見た目」の軸で他カテゴリと重複なし。`image_prompt_tags`(画像生成用の
英語タグ)を各候補に付ける。

| | name | 表示名 | コンセプト | core_traits 案 | image_prompt_tags(例) |
|---|---|---|---|---|---|
| ◎ | `twintails` | ツインテール | 左右に結った髪。活発・あどけなさの記号 | ツインテール / 活発な印象 / 髪を揺らす仕草 / あどけなさ | twintails, twin tails, ribbon hair ties |
| ◎ | `eyepatch` | 眼帯 | 片目を覆う眼帯。ミステリアス・厨二の記号 | 眼帯 / 隠された片目 / 意味深な雰囲気 / 触れられたくない過去感 | eyepatch, covered eye, mysterious |
| ◎ | `heterochromia` | オッドアイ | 左右で色の違う瞳。特別・非日常の記号 | 左右で違う瞳の色 / 特別な印象 / 見つめると惹き込む / 非日常性 | heterochromia, odd eyes, different colored eyes |
| ◎ | `tall` | 高身長・スタイル | 背が高くスタイルが良い。凛とした存在感 | 高身長 / 凛とした立ち姿 / 見下ろす視線 / 存在感 | tall, statuesque, long legs, model figure |
| ◎ | `kimono` | 和装・着物 | 着物や浴衣。古風・清楚・和の趣 | 和装 / 所作が丁寧 / 古風な佇まい / 季節感 | kimono, yukata, japanese clothes, traditional |
| ○ | `freckles` | そばかす | 頬のそばかす。素朴・親しみやすさ | そばかす / 素朴 / 健康的 / 親しみやすい | freckles, cheeks, natural, girl-next-door |
| ○ | `gothic_lolita` | ゴシック・ロリータ | フリルと黒基調の装い。耽美・人形的 | ゴスロリ装 / 耽美 / 人形めいた / こだわりの装飾 | gothic lolita, frills, victorian, doll-like |
| ○ | `ahoge` | アホ毛 | 一本跳ねた髪。感情のバロメーター、親しみ | アホ毛 / 感情で揺れる髪 / 天然な印象 / 愛嬌 | ahoge, cowlick, hair strand |
| ○ | `ponytail` | ポニーテール | 後ろで束ねた髪。快活・清潔感 | ポニーテール / 快活 / うなじ / きびきびした印象 | ponytail, tied hair, active |
| ○ | `scar` | 傷跡 | 頬や体の傷跡。歴戦・過去を背負う記号 | 傷跡 / 歴戦の印 / 過去を感じさせる / 触れると身構える | scar, battle scar, mark |

**第1弾推奨(visual +5)**: twintails, eyepatch, heterochromia, tall, kimono
→ 5 → 10

---

## hobby 候補(現 5 → 提案)

| | name | 表示名 | コンセプト | core_traits 案 | compatible / conflicts の当たり |
|---|---|---|---|---|---|
| ◎ | `art` | 絵・イラスト | 絵を描くのが好き。観察眼と表現、こだわり | 絵を描く / 観察眼 / 表現へのこだわり / 色彩に敏感 | compat: intellectual, mysterious / conflict: — |
| ◎ | `photography` | 写真 | 写真撮影が趣味。瞬間を捉える、被写体への眼差し | 瞬間を捉える / 構図を考える / 被写体をよく見る / 記録を残す | compat: laid_back, mysterious / conflict: — |
| ◎ | `gardening` | 園芸・ガーデニング | 植物を育てる。世話好き・穏やか、季節を愛でる | 植物を育てる / 世話好き / 穏やか / 季節に敏感 | compat: laid_back, protective / conflict: — |
| ◎ | `dance` | ダンス | 踊るのが好き。表現力と体の躍動、リズム感 | 踊るのが好き / 表現力豊か / リズム感 / 体で語る | compat: genki, idol / conflict: — |
| ◎ | `fortune_telling` | 占い | 占いが好き。神秘・直感、相手を読む | 占いが好き / 直感的 / 神秘を好む / 相手を読む | compat: mysterious, mahou_shoujo(speech) / conflict: pragmatist |
| ○ | `fashion` | ファッション・おしゃれ | 服やメイクが好き。トレンドと自己表現 | おしゃれ好き / トレンドに敏感 / 自己表現 / 人の装いも見る | compat: gyaru(speech), narcissist / conflict: — |
| ○ | `astronomy` | 天体観測 | 星を眺めるのが好き。ロマンと静けさ、知的好奇心 | 星を眺める / ロマンチスト / 静けさを好む / 知的好奇心 | compat: intellectual, mysterious / conflict: — |
| ○ | `crafting` | 手芸・ものづくり | 手作りが好き。器用さと根気、贈る喜び | 手先が器用 / 根気強い / 贈るのが好き / 細部にこだわる | compat: diligent, protective / conflict: klutz |
| ○ | `fishing` | 釣り | 釣りが好き。忍耐と静けさ、自然との対話 | 忍耐強い / 静けさを好む / 自然が好き / のんびり | compat: laid_back, stoic / conflict: — |
| ○ | `travel` | 旅行 | 旅が好き。好奇心と行動力、未知への憧れ | 好奇心旺盛 / 行動的 / 未知に惹かれる / 土地の話に詳しい | compat: go_getter, optimist / conflict: hikikomori |

**第1弾推奨(hobby +5)**: art, photography, gardening, dance, fortune_telling
→ 5 → 10

---

## まとめと確認事項

- **第1弾推奨(バランス重視 +15)**: 上記 ◎ 各5個。合計 **archetype 14 / visual 10 / hobby 10 = 201 → 216 属性**。
- 各属性は既存フォーマット準拠で作成する: BASE(ja)`core_traits`/`catchphrases`/`tone` + `content_i18n.en` + `examples`(会話形式2-3) + `compatible_archetypes`/`conflicts_with`(+visual は `image_prompt_tags`)。
- 属性数が変わるため、実装時は **README EN/JA・SKILL.md・REFERENCE.md・
  テストの count 契約・CHANGELOG** を同期し、`build_site.py` で `data.json` を再生成する(CLAUDE.md ルール)。

### 決めてほしいこと
1. **規模**: ◎ 各5個(+15)で進める? それとも ○ も含めて多め / 少なめ?
2. **取捨**: ◎/○ の中で「これは要る/要らない」があれば指定を。
3. **命名**: `student_council_president` は長い。`seitokaicho` や `class_president` など短縮案の希望があれば。

指示をもらえれば、選定分を一気に実装(YAML 作成 → テスト → ドキュメント同期 → PR)します。
