# 拡張バックログ: archetype / visual / hobby 大量候補 (2026-07-03)

「世の中にあるものを網羅する勢い」で候補を棚卸ししたマスターカタログ。
前回の [candidates doc](./2026-07-03-archetype-visual-hobby-candidates.md) を包含・拡張する。

**まだ実装しない**(選定・優先順位づけ用の backlog)。

## 方針・制約(全候補共通)

- **固有名詞・特定作品を含まない**(CC0 テンプレート方針)。型・役割・記号のみ。
- `attribute_name` は snake_case (`^[a-z][a-z0-9_]*$`)。
- カテゴリの意味:
  - **archetype** = 役割・立場・関係性(「何者か」)。
  - **visual** = 見た目(髪・目・体型・装い・非人間パーツ)。
  - **hobby** = 趣味・関心。
- **既存と重複しない**。speech 側に口調がある役割(`butler`/`oujo`/`sensei`/
  `miko` 等)は、既存の `shrine_maiden`(archetype)↔`miko`(speech)と同じく
  **立場軸で別属性として成立**する。該当は「※speech に口調あり」と注記。
- 実装時は README EN/JA・SKILL.md・REFERENCE.md・テスト count 契約・CHANGELOG を
  同期し `build_site.py` を再実行(CLAUDE.md ルール)。

凡例: **◎**=定番(第1弾候補) / **○**=有力 / **△**=ニッチ・要検討

現状: **archetype 9 / visual 5 / hobby 5**。
既存 archetype = childhood_friend, gamer_otaku, heroine, hikikomori, idol, mentor,
rival, robot_android, shrine_maiden。

---

# archetype 候補(役割・立場・関係性)

## A. 学園・青春
- ◎ `senpai` — 先輩: 頼れる年上、面倒見と余裕
- ◎ `kouhai` — 後輩: 慕う年下、初々しさと憧れ
- ◎ `student_council_president` — 生徒会長: 責任感とリーダーシップ
- ○ `class_rep` — 学級委員長: 真面目な取りまとめ役
- ○ `transfer_student` — 転校生: 新入りの緊張と好奇の目
- ○ `honor_student` — 優等生: 成績優秀・優等生の重圧
- ○ `delinquent` — 不良: 粗野な外見と情 ※speech `yankee` は口調
- ○ `teacher` — 教師: 導く立場 ※speech `sensei` は口調
- △ `school_nurse` — 保健室の先生: 気だるげな癒し役
- △ `club_ace` — 部のエース: 実力者の看板
- △ `prodigy` — 神童: 早熟の天才児

## B. 家族・関係性
- ◎ `big_sister` — 姉御・お姉さん的存在: 面倒見と包容 ※speech `onee_san` は口調
- ○ `big_brother` — 兄貴分: 頼れる年長者
- ○ `little_sister` — 妹的存在: 甘えと懐き ※speech `imouto` は口調
- ○ `little_brother` — 弟的存在: やんちゃな年下
- ○ `mother_figure` — 母性的存在: 無償の世話焼き ※speech `mama` は口調
- △ `father_figure` — 父性的存在: 厳しくも見守る
- △ `twin` — 双子: 対の存在・分身感
- △ `childhood_rival` — 幼馴染ライバル: childhood_friend + rival の交差

## C. 職業(現代)
- ◎ `detective` — 探偵: 観察と推理
- ○ `doctor` — 医者: 冷静な判断と責任
- ○ `nurse` — 看護師: 献身とケア
- ○ `scientist` — 科学者: 探究心と論理
- ○ `journalist` — 記者: 真実を追う嗅覚
- ○ `entrepreneur` — 起業家: 野心と行動力
- ○ `bartender` — バーテンダー: 聞き役・大人の余裕
- ○ `chef` — 料理人(職業): 厨房の職人気質 ※hobby `cooking` は趣味
- ○ `artist` — 芸術家: 表現への衝動 ※hobby `art` は趣味
- ○ `office_worker` — 会社員: 現実的な社会人 ※speech `ol`/`business` は口調
- △ `engineer` — 技術者: 実装と改善の人
- △ `lawyer` — 弁護士: 弁論と論理武装
- △ `police_officer` — 警官: 秩序と正義
- △ `athlete` — アスリート: 競技に生きる ※hobby `sports` は趣味
- △ `musician` — 音楽家(職業) ※hobby `music` は趣味

## D. 貴族・使用人・戦士(ファンタジー/歴史)
- ◎ `ojou_sama` — 令嬢: 気高く世間知らず ※speech `oujo`/`princess_speech` は口調
- ○ `butler` — 執事: 忠実で有能 ※speech `butler` は口調
- ○ `maid` — メイド: 献身と気配り
- ○ `knight` — 騎士: 忠誠と守護
- ○ `prince` — 王子: 高貴と責務
- ○ `noble` — 貴族: 特権階級の矜持
- ○ `bodyguard` — 護衛: 守る覚悟
- ○ `assassin` — 暗殺者: 影に生きる
- ○ `mercenary` — 傭兵: 契約と実利
- ○ `soldier` — 兵士: 規律と忠誠
- △ `commander` — 指揮官: 統率と決断
- △ `spy` — スパイ: 偽りと諜報
- △ `blacksmith` — 鍛冶屋: 職人の頑固さ
- △ `merchant` — 商人: 抜け目ない算段
- △ `adventurer` — 冒険者: 探索と自由 ※speech `yuuusha` は口調

## E. 神秘・魔法・非人間
- ◎ `witch` — 魔女: 神秘と知識 ※speech `mahou_shoujo`/`wizard` は口調
- ○ `vampire` — 吸血鬼: 妖艶と孤高
- ○ `angel` — 天使: 純粋と慈愛
- ○ `demon` — 悪魔: 誘惑と契約 ※speech `akuma_oujo` は口調
- ○ `goddess` — 女神: 超越と慈悲
- ○ `fairy` — 妖精: 気まぐれと無邪気
- ○ `ghost` — 幽霊: 儚さと未練
- ○ `kitsune` — 狐の妖: 化かしと神秘
- ○ `dragon` — 竜/竜人: 誇りと威厳
- ○ `cyborg` — サイボーグ: 機械と人間の狭間 ※archetype `robot_android` と近い/別実装
- ○ `alien` — 異星人: 価値観のズレ
- △ `oni` — 鬼: 荒々しさと孤独
- △ `mermaid` — 人魚: 異界の憧れ
- △ `elf` — エルフ: 長命と超然
- △ `reincarnated` — 転生者: 前世の記憶と達観
- △ `time_traveler` — 時間旅行者: 未来知と孤立

## F. 物語上の立場・スタンス
- ◎ `villain` — 悪役: 信念ある対立軸 ※speech `villainess` は口調
- ○ `antihero` — アンチヒーロー: 正義と逸脱の狭間
- ○ `lone_wolf` — 一匹狼: 群れない孤高
- ○ `best_friend` — 親友: 対等の信頼
- ○ `sidekick` — 相棒・助手: 支える立場
- ○ `apprentice` — 弟子: 学びと成長
- ○ `chosen_one` — 選ばれし者: 宿命と重圧
- ○ `underdog` — 這い上がり: 逆境からの反骨
- △ `leader` — リーダー: 統率と責任
- △ `mediator` — 調停役: 場を収める
- △ `outsider` — よそ者: 部外者の視点
- △ `celebrity` — 有名人: 注目される立場
- △ `ordinary_person` — 一般人/モブ: 平凡さの魅力
- △ `fallen_hero` — 堕ちた英雄: 栄光と喪失

---

# visual 候補(見た目)

すべて `image_prompt_tags`(画像生成用 英語タグ)を付ける。
既存 = animal_ears, glamorous, glasses, petite, silver_hair。

## A. 髪型
- ◎ `twintails` — ツインテール
- ◎ `ponytail` — ポニーテール
- ○ `braids` — 三つ編み
- ○ `hime_cut` — 姫カット
- ○ `bob_cut` — ボブ
- ○ `messy_hair` — 寝癖・ボサボサ
- ○ `ahoge` — アホ毛(感情で揺れる一本毛)
- △ `drill_hair` — 縦ロール
- △ `side_ponytail` — サイドテール
- △ `hair_bun` — お団子ヘア
- △ `blunt_bangs` — ぱっつん前髪
- △ `long_hair` — ロングヘア
- △ `short_hair` — ショートヘア

## B. 髪色
- ○ `blonde` — 金髪
- ○ `pink_hair` — ピンク髪
- ○ `black_hair` — 黒髪(艶やか)
- ○ `red_hair` — 赤髪
- ○ `blue_hair` — 青髪
- △ `white_hair` — 白髪(silver とは別質感)
- △ `inner_color` — インナーカラー/メッシュ
- △ `gradient_hair` — グラデ毛

## C. 目
- ◎ `heterochromia` — オッドアイ
- ○ `sharp_eyes` — つり目(勝ち気)
- ○ `droopy_eyes` — たれ目(柔和)
- ○ `jitome` — ジト目(半眼)
- ○ `eyepatch` — 眼帯
- △ `red_eyes` — 赤い瞳
- △ `golden_eyes` — 金色の瞳
- △ `eyebags` — 目の下の隈

## D. 体型・身長
- ◎ `tall` — 高身長・スタイル
- ○ `slender` — スレンダー
- ○ `muscular` — 筋肉質・鍛えた体
- △ `chubby` — ぽっちゃり
- △ `androgynous` — 中性的

## E. 肌・顔の記号
- ○ `freckles` — そばかす
- ○ `tan` — 日焼け・褐色肌
- ○ `fang` — 八重歯
- ○ `mole` — 泣きぼくろ
- ○ `scar` — 傷跡
- △ `pale_skin` — 色白
- △ `blush` — 常に頬染め

## F. 装い・服飾
- ◎ `kimono` — 和装・着物
- ○ `gothic_lolita` — ゴスロリ
- ○ `maid_outfit` — メイド服
- ○ `uniform` — 制服
- ○ `suit` — スーツ
- ○ `lab_coat` — 白衣
- ○ `hoodie` — パーカー
- ○ `ribbon` — リボン
- ○ `choker` — チョーカー
- △ `armor` — 鎧
- △ `headphones` — ヘッドホン常時
- △ `bandages` — 包帯
- △ `gloves` — 手袋
- △ `hat` — 帽子

## G. 非人間パーツ(ファンタジー)
- ○ `horns` — 角
- ○ `tail` — 尻尾
- ○ `wings` — 翼
- ○ `pointed_ears` — 尖った耳(エルフ耳)
- ○ `fangs` — 牙
- △ `halo` — 光輪
- △ `scales` — 鱗
- △ `glowing_eyes` — 発光する瞳

---

# hobby 候補(趣味・関心)

既存 = cooking, gamer, music, reading, sports。

## A. 創作・表現
- ◎ `art` — 絵・イラスト
- ◎ `photography` — 写真
- ◎ `dance` — ダンス
- ○ `singing` — 歌
- ○ `writing` — 執筆・小説
- ○ `crafting` — 手芸・ものづくり
- ○ `cosplay` — コスプレ
- ○ `makeup` — メイク
- △ `calligraphy` — 書道
- △ `pottery` — 陶芸
- △ `flower_arrangement` — 華道
- △ `knitting` — 編み物

## B. アウトドア・運動
- ○ `martial_arts` — 武道・格闘技
- ○ `hiking` — 登山・ハイキング
- ○ `camping` — キャンプ
- ○ `fishing` — 釣り
- ○ `swimming` — 水泳
- ○ `cycling` — サイクリング
- ○ `yoga` — ヨガ
- ○ `gardening` — 園芸・ガーデニング
- △ `running` — ランニング
- △ `surfing` — サーフィン
- △ `skateboarding` — スケボー

## C. 知的・収集
- ○ `programming` — プログラミング
- ○ `astronomy` — 天体観測
- ○ `board_games` — ボードゲーム・将棋
- ○ `collecting` — 収集(コレクター)
- ○ `history_buff` — 歴史好き
- ○ `languages` — 語学
- △ `puzzles` — パズル
- △ `model_building` — プラモデル
- △ `trains` — 鉄道

## D. ライフスタイル・食
- ○ `baking` — お菓子作り
- ○ `cafe_hopping` — カフェ巡り
- ○ `tea_ceremony` — 茶道
- ○ `coffee` — コーヒー
- ○ `fashion` — ファッション・おしゃれ
- ○ `travel` — 旅行
- ○ `movies` — 映画鑑賞
- ○ `karaoke` — カラオケ
- ○ `pet_care` — ペット・動物好き
- △ `shopping` — 買い物
- △ `wine` — ワイン

## E. 神秘・ニッチ
- ◎ `fortune_telling` — 占い
- ○ `meditation` — 瞑想
- ○ `occult` — オカルト・都市伝説
- △ `aromatherapy` — アロマ
- △ `birdwatching` — 野鳥観察
- △ `bonsai` — 盆栽

---

# 集計と進め方

**候補総数(概算)**: archetype ~65 / visual ~55 / hobby ~50 = **~170 候補**。

段階導入の提案(count 契約の同期は各弾で 1 回):

| 弾 | 内容 | 追加数 | 到達 |
|---|---|---|---|
| 第1弾 | 各カテゴリ ◎ のみ | +13 | 214 |
| 第2弾 | ○ を投入 | +90 前後 | 300+ |
| 第3弾 | △(ニッチ)を精査して投入 | 残り | 370 前後 |

### 決めてほしいこと
1. **どこまで採用するか**: ◎ のみ / ◎+○ / ◎+○+△(ほぼ全部)。
2. **カテゴリ間バランス**: 均等に増やす? archetype を厚めに?
3. **段階導入 vs 一括**: 1 PR に何個まで載せるか(レビューのしやすさとトレードオフ)。
4. **命名の統一**: 長い名前(`student_council_president`, `flower_arrangement`)を
   短縮するか、正式名で通すか。

方向が決まれば、その範囲を一気に YAML 化 → テスト → ドキュメント同期 → PR まで進めます。
