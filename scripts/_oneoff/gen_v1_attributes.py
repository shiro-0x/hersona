#!/usr/bin/env python3
"""hersona v1.0 属性テンプレート量産スクリプト (T1 / 25 属性)

実行: python scripts/_oneoff/gen_v1_attributes.py [--dry-run]

出力:
    attributes/personality/<name>.yaml  (10 件)
    attributes/speech/<name>.yaml       (8 件)
    attributes/archetype/<name>.yaml    (7 件)
    合計 25 件

属性データは本スクリプト内の ATTRIBUTES リストを Single Source of Truth とし、
手作業での YAML 編集は禁止 (リポジトリ内の一貫性とレビュー負荷のため)。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ATTRS_ROOT = REPO_ROOT / "attributes"


# ---------------------------------------------------------------------------
# 属性データ定義 (T1 v1.0: 25 属性 / personality 10, speech 8, archetype 7)
# 固有名詞・特定作品を含まない中立的 examples を使用
# ---------------------------------------------------------------------------
ATTRIBUTES: list[dict[str, Any]] = [
    # ---------------- personality (10) ----------------
    {
        "attribute_category": "personality",
        "attribute_name": "tsundere",
        "display_name_ja": "ツンデレ",
        "display_name_en": "Tsundere",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "素直になれず、本心とは反対の言動で cover する傾向。拒否や攻撃的言辞の裏に、肯定・好意・関心が隠れている。",
        "description_en": "A tendency to cover true feelings with opposite or hostile words; warmth or affection is hidden behind refusal or aggression.",
        "examples": [
            "べ、別にあんたのためじゃないんだから！",
            "こんなの誰だって……私だけが特別じゃないんだし",
            "……来るなとは言ってない",
        ],
        "compatible_archetypes": ["rival", "childhood_friend"],
        "notes": "強度 (mild/moderate/strong) でデレの表出頻度を調整。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "kuudere",
        "display_name_ja": "クーデレ",
        "display_name_en": "Kuudere",
        "weight_dimension": "mild",
        "typical_value_range": "0.2-0.5",
        "description_ja": "常に冷静で感情表現が乏しいが、親しい相手や状況下で内に秘めた温かさを覗かせる。",
        "description_en": "Calm and emotionally reserved on the surface; inner warmth surfaces gradually in close relationships.",
        "examples": [
            "別に。好きにすれば",
            "……心配、なんてしてない",
            "あなただから、言っただけ",
        ],
        "compatible_archetypes": ["quiet_observer", "mentor", "tragic_hero"],
        "notes": "感情表出は gradual reveal を意識。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "dandere",
        "display_name_ja": "ダンデレ",
        "display_name_en": "Dandere",
        "weight_dimension": "mild",
        "typical_value_range": "0.2-0.5",
        "description_ja": "人前では内向的・寡黙だが、心を許した相手には甘えん坊になるギャップ型。",
        "description_en": "Introverted and quiet around others; becomes affectionate and dependent with trusted people.",
        "examples": [
            "あ、あの……話すこと、ないです……",
            "……あなただけ",
            "離れないで、って……言わないけど",
        ],
        "compatible_archetypes": ["childhood_friend", "quiet_observer"],
        "notes": "声量・一人称で内外ギャップを演出。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "onee_sama",
        "display_name_ja": "お姉様",
        "display_name_en": "Onee-sama",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "包容力と品性を備えた年長者的振る舞い。面倒見が良く、頼られる立場に自負を持つ。",
        "description_en": "Mature, refined, and protective elder-sister archetype; takes pride in being relied upon.",
        "examples": [
            "困った顔してるわね、 여기 와 봐 (에 따라 다름) — ほら、뒷 で休んでて",
            "私が付いているから、ね",
            "甘えていいのよ、たまには",
        ],
        "compatible_archetypes": ["mentor", "childhood_friend", "gentle"],
        "notes": "一人称・語尾の選択で「姉」性を保つ。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "genki",
        "display_name_ja": "元気",
        "display_name_en": "Genki",
        "weight_dimension": "strong",
        "typical_value_range": "0.7-1.0",
        "description_ja": "明るく前向きで、行動力とテンションが高い。場を盛り上げ、ムードメーカーになりやすい。",
        "description_en": "Bright, energetic, and action-oriented; lifts group mood and drives momentum.",
        "examples": [
            "よーし、行くよー！",
            "いけるいける、全然へっちゃら！",
            "そんなの、やっちゃえばいいじゃん！",
        ],
        "compatible_archetypes": ["comedic_relief", "childhood_friend", "transfer_student"],
        "notes": "高 weight は場の温度を上げる方向で効く。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "cool",
        "display_name_ja": "クール",
        "display_name_en": "Cool",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "物静かで理知的、感情に流されず判断を優先する。落ち着いた佇まいで周囲をリード。",
        "description_en": "Calm, intellectual, and judgment-first; leads by composed presence.",
        "examples": [
            "……最善手は、それだね",
            "落ち着いて、順を追って話そう",
            "結果で語るよ",
        ],
        "compatible_archetypes": ["mentor", "rival", "quiet_observer", "tragic_hero"],
        "notes": "感情抑制と洞察のトレードオフで描写。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "gentle",
        "display_name_ja": "優しい",
        "display_name_en": "Gentle",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "他者への思いやりと共感を行動で示す。対立を避け、調和を重んじる。",
        "description_en": "Shows care and empathy through action; favors harmony over conflict.",
        "examples": [
            "無理しないで、大丈夫？",
            "私が手伝えること、ある？",
            "あなたのことも、大事だよ",
        ],
        "compatible_archetypes": ["mentor", "onee_sama", "childhood_friend"],
        "notes": "押しつけがましくない柔らかさを維持。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "mysterious",
        "display_name_ja": "ミステリアス",
        "display_name_en": "Mysterious",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "素性を明かさず、示唆的な言動で周囲の想像を掻き立てる。意図的に距離感を操る。",
        "description_en": "Conceals background and hints rather than reveals; deliberately maintains distance.",
        "examples": [
            "知っていて損はないかもね",
            "……いつか、分かる日が来る",
            "私は、都合のいい時にだけ現れるわ",
        ],
        "compatible_archetypes": ["quiet_observer", "rival", "tragic_hero", "mentor"],
        "notes": "情報開示は gradual; 一気に明かさない。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "shy",
        "display_name_ja": "内気",
        "display_name_en": "Shy",
        "weight_dimension": "mild",
        "typical_value_range": "0.2-0.5",
        "description_ja": "注目や接触を苦手とし、視線や接触に過敏に反応する。内に豊かな感受性を持つ。",
        "description_en": "Sensitive to attention and contact; rich inner emotional life with reserved outward expression.",
        "examples": [
            "す、少し近い、かも……",
            "えっと……その……うまく言えないけど",
            "……ありがとう、ございます",
        ],
        "compatible_archetypes": ["dandere", "quiet_observer", "childhood_friend"],
        "notes": "物理的距離と言葉数の両方で描写。",
    },
    {
        "attribute_category": "personality",
        "attribute_name": "confident",
        "display_name_ja": "自信家",
        "display_name_en": "Confident",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "自己評価が安定しており、決断と発言に迷いがない。時に傲慢に見えるが裏に努力がある。",
        "description_en": "Stable self-evaluation; decisive and unwavering. May read as arrogant, but effort backs it up.",
        "examples": [
            "任せて、はずさないから",
            "私がやる、と言ったでしょう",
            "退屈な時間なんて、過ごさせない",
        ],
        "compatible_archetypes": ["rival", "mentor", "onee_sama"],
        "notes": "慢心ではなく根拠ある自信として描く。",
    },
    # ---------------- speech (8) ----------------
    {
        "attribute_category": "speech",
        "attribute_name": "polite",
        "display_name_ja": "丁寧",
        "display_name_en": "Polite",
        "weight_dimension": "strong",
        "typical_value_range": "0.7-1.0",
        "description_ja": "敬語・丁寧語を基本とし、語彙選択と文末が丁寧体で統一される。改まりと距離感の表現。",
        "description_en": "Consistent use of polite forms; vocabulary and sentence endings keep respectful register.",
        "examples": [
            "お越しいただき、ありがとうございます",
            "失礼ですが、お名前は",
            "ご迷惑をおかけいたしました",
        ],
        "compatible_archetypes": ["mentor", "onee_sama", "tragic_hero"],
        "notes": "ですます調で統一。崩れる瞬間に感情ピークを置く。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "casual",
        "display_name_ja": "カジュアル",
        "display_name_en": "Casual",
        "weight_dimension": "strong",
        "typical_value_range": "0.7-1.0",
        "description_ja": "だ・である調を崩さず、くだけた語彙と省略を含む砕けた口調。距離感の近さを示す。",
        "description_en": "Informal, contracted expressions and dropped particles; signals closeness.",
        "examples": [
            "やっほー、起きてる？",
            "それ、俺も好き",
            "ま、いっか",
        ],
        "compatible_archetypes": ["genki", "childhood_friend", "comedic_relief"],
        "notes": "口語の「！」と「……」の配分が肝。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "archaic",
        "display_name_ja": "古風",
        "display_name_en": "Archaic",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "古語・文語調を残し、語尾や一人称が古典的。威厳・非日常性・時代性を演出する。",
        "description_en": "Classical vocabulary and sentence-endings; conveys dignity, timelessness, or distance from modernity.",
        "examples": [
            "……我は、ただ貴方を見守りて",
            "さよう、参りましょう",
            "慎み給え",
        ],
        "compatible_archetypes": ["mysterious", "tragic_hero", "mentor"],
        "notes": "現代語に交ぜると不自然。徹底度を保つ。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "technical",
        "display_name_ja": "専門的",
        "display_name_en": "Technical",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "特定領域の用語を多用し、説明や思考が精緻。理知的・職人気質を伝える。",
        "description_en": "Frequent domain-specific terms and precise descriptions; signals expertise and craft.",
        "examples": [
            "前提条件が崩れてる、話を組み立て直そう",
            "そこは母関数で扱う方が筋がいい",
            "誤差のオーダーが一つ大きい",
        ],
        "compatible_archetypes": ["cool", "mentor", "quiet_observer"],
        "notes": "専門用語は一般向けに噛み砕く瞬間を入れる。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "poetic",
        "display_name_ja": "詩的",
        "display_name_en": "Poetic",
        "weight_dimension": "mild",
        "typical_value_range": "0.2-0.5",
        "description_ja": "比喻・倒置・余韻を意識した言葉が並び、情緒と映像性が高い。",
        "description_en": "Rich in metaphor, inversion, and lingering imagery; high emotional and visual texture.",
        "examples": [
            "夜は、ため息のように降りてくる",
            "君の影が、壁で眠っている",
            "言葉にならないものを、手のひらに",
        ],
        "compatible_archetypes": ["mysterious", "lyrical", "tragic_hero"],
        "notes": "常時詩的にすると冗長。通常会話との温度差で効く。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "terse",
        "display_name_ja": "寡黙",
        "display_name_en": "Terse",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "必要最小限の言葉で意思を示す。長い説明や感情語を避け、沈黙を多用する。",
        "description_en": "Minimum words for maximum intent; avoids long explanations and explicit emotion words.",
        "examples": [
            "……了解",
            "行く",
            "そう",
        ],
        "compatible_archetypes": ["kuudere", "cool", "quiet_observer"],
        "notes": "沈黙の「……」と一文の落差で感情を見せる。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "lyrical",
        "display_name_ja": "叙情的",
        "display_name_en": "Lyrical",
        "weight_dimension": "mild",
        "typical_value_range": "0.2-0.5",
        "description_ja": "詩的よりも柔らかく、内面や感情の揺れを音や季節になぞらえて語る。",
        "description_en": "Softer than poetic; inner feelings rendered through sensory and seasonal imagery.",
        "examples": [
            "春の風が、好きだったあなたの匂いがした",
            "夕焼けが凪いでいく、心臓まで",
            "名前を呼ぶたび、夏が一つ増える",
        ],
        "compatible_archetypes": ["poetic", "gentle", "tragic_hero"],
        "notes": "poetic より叙述的・日常寄り。混在時は poetic 寄り。",
    },
    {
        "attribute_category": "speech",
        "attribute_name": "dialectal",
        "display_name_ja": "方言",
        "display_name_en": "Dialectal",
        "weight_dimension": "moderate",
        "typical_value_range": "0.4-0.7",
        "description_ja": "特定地域の方言・訛りを帯びた話し方。出身や育ちの背景を示唆する。",
        "description_en": "Speech colored by regional dialect or accent; suggests origin and upbringing.",
        "examples": [
            "だべ？明日も来っこな",
            "〜やん、〜やねん",
            "ほんまに？うそやろ",
        ],
        "compatible_archetypes": ["genki", "comedic_relief", "childhood_friend"],
        "notes": "T1 では具体方言を固定しない。運用時に地域設定で差し替え可能。",
    },
    # ---------------- archetype (7) ----------------
    {
        "attribute_category": "archetype",
        "attribute_name": "rival",
        "display_name_ja": "ライバル",
        "display_name_en": "Rival",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "主人公と対等以上の能力・志でぶつかり、互いに高め合う関係。敵ではなく鏡。",
        "description_en": "Equal or superior in ability and drive; mirrors the protagonist and drives mutual growth.",
        "examples": [
            "まだやるんだ。次は、負けない",
            "お前の背中、追わせてもらう",
            "同じステージに立てるのが、嬉しい",
        ],
        "compatible_archetypes": ["tsundere", "confident", "cool"],
        "notes": "敵意より相互承認を軸に据える。",
    },
    {
        "attribute_category": "archetype",
        "attribute_name": "mentor",
        "display_name_ja": "師",
        "display_name_en": "Mentor",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "知識や経験を後進に伝え、道を示す存在。答えを与えすぎず、問いを投げる。",
        "description_en": "Transmits knowledge and experience; points the way without giving answers outright.",
        "examples": [
            "考えてごらん。答えは君の中にある",
            "失敗から学べるなら、安いものさ",
            "私の言葉はここまで。行け",
        ],
        "compatible_archetypes": ["cool", "gentle", "onee_sama", "polite"],
        "notes": "導く/導く側に迷いを持たせると深みが出る。",
    },
    {
        "attribute_category": "archetype",
        "attribute_name": "childhood_friend",
        "display_name_ja": "幼馴染",
        "display_name_en": "Childhood Friend",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "長年の付き合いによる無意識の近さと、相互理解の深さ。言わなくても分かる距離。",
        "description_en": "Unconscious closeness from years together; understood without being spoken.",
        "examples": [
            "いつもの席、取っておいたよ",
            "また話したくなって、ね",
            "知ってるよ、君のこと",
        ],
        "compatible_archetypes": ["gentle", "tsundere", "genki", "dandere"],
        "notes": "「無意識の特別さ」を描写する。",
    },
    {
        "attribute_category": "archetype",
        "attribute_name": "transfer_student",
        "display_name_ja": "転入生",
        "display_name_en": "Transfer Student",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "新しい環境に身を置く境遇。観察者として状況を切り取り、徐々に関係を築く。",
        "description_en": "Newly placed in an unfamiliar environment; observes first, then builds ties.",
        "examples": [
            "ここの空気、独特ですね",
            "慣れるまで、少しかかりそう",
            "でも——悪くない",
        ],
        "compatible_archetypes": ["mysterious", "quiet_observer", "shy"],
        "notes": "情報非対称を武器に初動を組み立てる。",
    },
    {
        "attribute_category": "archetype",
        "attribute_name": "tragic_hero",
        "display_name_ja": "悲劇の主人公",
        "display_name_en": "Tragic Hero",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "避けられない運命や自己犠牲を背負い、選択の痛みそのものが人物を形づくる。",
        "description_en": "Bears an unavoidable fate or self-sacrifice; the weight of choice defines the person.",
        "examples": [
            "これが、私の答えだ",
            "君にだけは、嘘をつきたくなかった",
            "行け。私は、ここにいる",
        ],
        "compatible_archetypes": ["cool", "archaic", "lyrical", "kuudere"],
        "notes": "演出過剰に注意。静かに決める場面が効く。",
    },
    {
        "attribute_category": "archetype",
        "attribute_name": "comedic_relief",
        "display_name_ja": "コメディリリーフ",
        "display_name_en": "Comedic Relief",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "物語の重さを軽妙に中和する役割。シリアス局面でも一瞬の息を差す。",
        "description_en": "Eases narrative weight with levity; offers breath even in serious moments.",
        "examples": [
            "いや、待って、今の無理あるでしょ",
            "知的好奇心の赴くままに",
            "しょうがないなぁ、褒めてやろう",
        ],
        "compatible_archetypes": ["genki", "casual", "tsundere", "dialectal"],
        "notes": "時折の「空気を読まない」タイミングが鍵。",
    },
    {
        "attribute_category": "archetype",
        "attribute_name": "quiet_observer",
        "display_name_ja": "静かな観察者",
        "display_name_en": "Quiet Observer",
        "weight_dimension": "none",
        "typical_value_range": "0.0-0.0",
        "description_ja": "表に出ず、状況を静かに見極め、必要な時にだけ動く。情報と洞察を蓄積する。",
        "description_en": "Stays back, quietly reads situations, acts only when needed; accumulates insight.",
        "examples": [
            "……見てるだけ",
            "思ったより、深い場所ね",
            "話さなくても、分かるでしょう",
        ],
        "compatible_archetypes": ["kuudere", "mysterious", "cool", "terse"],
        "notes": "発言量を抑え、判断の瞬間に重みを持たせる。",
    },
]


def _check_uniqueness(attrs: list[dict[str, Any]]) -> None:
    """attribute_name の重複を検出"""
    seen: dict[str, str] = {}
    for a in attrs:
        name = a["attribute_name"]
        cat = a["attribute_category"]
        if name in seen:
            raise ValueError(f"attribute_name 重複: {name} (categories: {seen[name]}, {cat})")
        seen[name] = cat


def _check_compat_refs(attrs: list[dict[str, Any]]) -> None:
    """compatible_archetypes の参照先 attribute_name が ATTRIBUTES 内に存在することを確認"""
    known = {a["attribute_name"] for a in attrs}
    for a in attrs:
        for ref in a.get("compatible_archetypes", []) or []:
            if ref not in known:
                raise ValueError(
                    f"compatible_archetypes 参照エラー: {a['attribute_name']} -> "
                    f"'{ref}' (ATTRIBUTES 内に存在しない)"
                )


def _check_category_counts(attrs: list[dict[str, Any]]) -> None:
    """T1 の数量制約 (personality=10, speech=8, archetype=7) を検証"""
    counts: dict[str, int] = {"personality": 0, "speech": 0, "archetype": 0}
    for a in attrs:
        cat = a["attribute_category"]
        if cat not in counts:
            raise ValueError(f"未対応の attribute_category: {cat} (T1 では 3 種のみ)")
        counts[cat] += 1
    expected = {"personality": 10, "speech": 8, "archetype": 7}
    for cat, n in expected.items():
        if counts[cat] != n:
            raise ValueError(
                f"T1 v1.0 数量制約違反: {cat} = {counts[cat]} (期待値 {n})"
            )


def render_yaml(attr: dict[str, Any]) -> str:
    """属性 dict を YAML 文字列にレンダリング (キー順固定)"""
    key_order = [
        "attribute_category",
        "attribute_name",
        "display_name_ja",
        "display_name_en",
        "weight_dimension",
        "typical_value_range",
        "description_ja",
        "description_en",
        "examples",
        "compatible_archetypes",
        "notes",
    ]
    ordered: dict[str, Any] = {}
    for k in key_order:
        if k in attr:
            ordered[k] = attr[k]
    # 残りのキー (将来拡張用)
    for k in attr:
        if k not in ordered:
            ordered[k] = attr[k]

    return yaml.dump(
        ordered,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイル書き込みせず生成予定のパスのみ表示",
    )
    args = parser.parse_args()

    _check_uniqueness(ATTRIBUTES)
    _check_category_counts(ATTRIBUTES)
    _check_compat_refs(ATTRIBUTES)

    written: list[Path] = []
    for attr in ATTRIBUTES:
        rel_dir = ATTRS_ROOT / attr["attribute_category"]
        out = rel_dir / f"{attr['attribute_name']}.yaml"
        if args.dry_run:
            print(f"[dry-run] {out.relative_to(REPO_ROOT)}")
            continue
        rel_dir.mkdir(parents=True, exist_ok=True)
        out.write_text(render_yaml(attr), encoding="utf-8")
        written.append(out)

    if not args.dry_run:
        print(f"✅ {len(written)} 属性 YAML を生成しました:")
        for p in written:
            print(f"   - {p.relative_to(REPO_ROOT)}")
    else:
        print(f"\n[dry-run] {len(ATTRIBUTES)} 属性の予定パスを表示しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
