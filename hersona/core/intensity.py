"""強度指標 (intensity metric)。

ROADMAP の「強度指標 (intensity metric) ★計画 (仕様確定済み・未実装)」を実装する
core ロジック。出力テキストの「形」(語尾一致率 + 口癖密度 + 一人称命中率) を
**表層のみ・決定的** に採点し、期待バンドと比較して status (pass / under / over) を返す。

設計の割り切り (ROADMAP / IMPLEMENTATION_GUIDE §4.1 合意済み):
- LLM 不使用。再現性優先、gaming 可は許容。
- 一人称 (first_person フィールド) が schema に追加されたため B4 で 3 軸目として採用。
- speech 属性が 1 つも無いブレンドは測定 skip (語尾軸・一人称軸が無いため)。
- 対応言語: ja (語尾+一人称) / en・zh・ko (lexical_markers、A-3 sharpen-and-grow)。
  それ以外の content_lang は unsupported_lang として skip。
"""
from __future__ import annotations

from dataclasses import dataclass

from hersona.core.i18n import tr
from hersona.core.weight import (
    WEIGHT_GUIDANCE,
    WeightLevel,
    coerce_level,
    normalize_catchphrase,
)

_BASE_PROMPT = {
    "en": (
        "Before you answer, re-read the persona spec and self-audit your draft:\n"
        "1. Have you used the listed catchphrases (or consciously omitted them)?\n"
        "2. Do your sentence endings match the registered register?\n"
        "3. Did any `conflicts_with` attribute leak into the response?\n"
        "4. Does the response's intensity match the {weight} level ({band})?\n"
    ),
    "ja": (
        "応答前に人格仕様を再読し、ドラフトを自己採点してください:\n"
        "1. 口癖 (catchphrases) は実際に使われているか (または意図的に省略したか)\n"
        "2. 文末・語尾は登録されたレジスタと一致するか\n"
        "3. `conflicts_with` を持つ属性が混入していないか\n"
        "4. 出力の強度は {weight} レベル ({band}) に届いているか\n"
    ),
}

# §3 P2b (docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md): naturalness (AI 臭) 版の
# 自己点検。「人間に AI くさいと指摘された」フレーミング + §2 カタログ (A/B/D) の
# 観察観点。C (文長・漢語連続) は自己監査で判断しにくいため対象外 (§4-4 割り切り)。
_NATURALNESS_CHECK_PROMPT = {
    "en": (
        "1. Any stock opener/closer (\"Certainly!\", \"I hope this helps\"), meta "
        "preamble, or AI self-reference?\n"
        "2. Repeated contrast/triplet rhythm, or every sentence hedged the same way?\n"
        "3. Did you answer a conversational question with an unneeded bullet list, "
        "headers, or a boilerplate disclaimer?\n"
        "4. Would this sentence read the same no matter who wrote it — where's this "
        "persona's own bias or specificity?\n"
    ),
    "ja": (
        "1. 定型の書き出し・締め (かしこまりました/参考になれば幸いです 等) や、AI への"
        "自己言及を使っていないか\n"
        "2. 同じ対比・三拍子のリズムの連打や、文末が全部同じヘッジになっていないか\n"
        "3. 会話の質問に対して、不要な箇条書き・見出し・定型の注意書きで答えていないか\n"
        "4. この一文、誰が書いても同じにならないか — このペルソナならではの偏りや"
        "具体性はあるか\n"
    ),
}

# 文末判定時の句読点・記号 (半角全角両対応)
_PUNCT_STRIP = "。．.！!？? 　"

# --- metric v2 (2026-07-12) --------------------------------------------------
# 公式比較実行 (docs/BENCHMARKS.md 2026-07-11) が全条件 maintenance 0% になった
# 根因は「モデルが人格を維持していても採点器が拾えない」測定側の欠陥 4 つ:
#   1. 語尾照合が literal endswith のみ → 活用形 (ました/ません) と終助詞
#      (ね/よ/わ/の…) 付きの完璧な keigo が全部不一致
#   2. personality 属性の catchphrases が採点対象外 → tsundere の「誰が気に
#      するものかしら」を verbatim で言っても 0 点
#   3. first_person「私（わたくし）」が読み仮名括弧ごと 1 トークン扱い →
#      「私」が永遠にヒットしない
#   4. 口癖密度が「毎文 1 口癖」で満点の正規化 → 注入ディレクティブ自身が
#      「口癖を毎回繰り返すな」と指示しており、指示と採点が矛盾
# 以下の定数・ヘルパーは上記を決定的なまま塞ぐ最小セット。スコアの絶対値は
# v1 と互換しない (旧公表値との比較不可 — CHANGELOG / BENCHMARKS.md 参照)。

# 文末から剥がしてよい終助詞・間投助詞など (1 文字ずつ、最大 3 文字)
_JA_TRAIL_PARTICLES = "ねよなのかしさもんぞぜわがっ〜ーぁぃぅぇぉ"

# 文末から 1 回だけ剥がしてよい接続助詞 (言いさし形: 〜ですけれど / 〜ますので)
_JA_TRAIL_CONJUNCTIONS = (
    "けれども", "けれど", "けども", "けど", "から", "ので", "のに", "って",
)

# 丁寧語尾の決定的活用展開: 登録語尾が ます/です で終わる場合のみ、
# 同じ丁寧レジスタの活用形を照合対象に加える (ございます→ございません 等)。
_JA_POLITE_VARIANTS = {
    "ます": ("ました", "ません", "ましょう", "まして", "ませ"),
    "です": ("でした", "でしょう"),
}

# 口癖・一人称の natural cadence: 4 文に 1 回で軸満点。
# 「毎文口癖」は response_style_directive が明示的に禁じる話し方であり、
# 指標がそれを要求してはいけない (§metric v2 根因 4)。
_HIT_CADENCE = 0.25

# 口癖照合用の前後 strip (収録形の「べ、別に……」が実出力の「べ、別に」に一致するように)
_CATCHPHRASE_MATCH_STRIP = "…。、！？!?.,～〜 　"


@dataclass
class IntensityReport:
    """強度指標の採点結果。"""

    score: float  # 0-100
    endings_rate: float  # 0-1: 文末が sentence_endings に一致した割合
    catchphrase_hits: int  # catchphrases 出現回数
    sentence_count: int  # 採点対象文数
    band: tuple[int, int]  # 期待バンド (lo, hi)
    status: str  # "pass" / "under" / "over"
    lang: str = "ja"  # 採点対象 (speech 属性) のコンテンツ言語
    first_person_hits: int = 0  # first_person 一人称の出現回数


def _has_japanese(text: str) -> bool:
    """text に日本語 (ひらがな/カタカナ/漢字) が含まれるか。"""
    return any(
        "぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" or ch == "ー"
        for ch in text
    )


def _has_kana(text: str) -> bool:
    """text に仮名 (ひらがな/カタカナ) が含まれるか (日本語混入の判定用)。

    漢字 (一-鿿) は中国語 (簡体字/繁体字) と共有される Unicode ブロックのため、
    zh の言語不一致判定には使えない (ja/zh は判別できない場合がある。§A-3 の割り切り)。
    仮名は ja にしかほぼ出現しないため、zh 採点における「ja 混入」シグナルとして使う。
    """
    return any("぀" <= ch <= "ヿ" or ch == "ー" for ch in text)


def _has_hangul(text: str) -> bool:
    """text にハングル (音節・字母) が含まれるか。"""
    return any(
        "가" <= ch <= "힣" or "ㄱ" <= ch <= "ㆎ"
        for ch in text
    )


def content_language(attributes: list[dict]) -> str:
    """ブレンドのコンテンツ言語を speech 属性の content_lang から決める。

    speech 属性の最初の ``content_lang`` を採用。未指定/speech 無しは既定 ``ja``。
    """
    for a in attributes:
        if a.get("attribute_category") == "speech" and a.get("content_lang"):
            return str(a["content_lang"])
    return "ja"


def resolve_content_field(attr: dict, key: str, lang: str) -> tuple[object, bool]:
    """言語拘束コンテンツ (catchphrases / tone / core_traits) を lang に解決する。

    BASE (トップレベルのキー) の言語は属性の ``content_lang`` (未指定は ``ja``)。
    要求 lang が属性の BASE 言語と一致すれば BASE を、異なれば
    ``content_i18n.<lang>.<key>`` を優先する。
    戻り値 ``(value, is_native)``:
    - ``is_native=True``  : value はその言語でネイティブ (BASE 一致 or 解決済み)
    - ``is_native=False`` : BASE 値しか無く lang と不一致 (呼び出し側で除外判断)
    """
    base = attr.get(key)
    attr_lang = str(attr.get("content_lang") or "ja")
    if not lang or attr_lang == lang:
        return base, True
    sub = (attr.get("content_i18n") or {}).get(lang) or {}
    if sub.get(key):
        return sub[key], True
    return base, False


def skip_reason(text: str, attributes: list[dict]) -> str | None:
    """強度測定を skip すべきか判定し、理由コードを返す (測定可なら None)。

    - ``"no_speech"``     : speech 属性のシグナル (語尾 / first_person / lexical_markers) が無い
    - ``"unsupported_lang"``: コンテンツ言語が ja / en / zh / ko 以外 (採点ロジック未対応)
    - ``"lang_mismatch"`` : コンテンツ言語と出力テキストの言語が食い違う

    zh / ko (A-3, sharpen-and-grow) は en と同じ ``lexical_markers`` 経路で採点する
    (native zh/ko 6 属性は authoring 時点で語気助詞・語尾を lexical_markers として
    持つため、sentence_endings のバックフィルは不要だった)。
    """
    endings, markers, _, first_persons = _collect_speech_signals(attributes)
    lang = content_language(attributes)
    if lang == "ja":
        if not endings and not first_persons:
            return "no_speech"
        if text.strip() and not _has_japanese(text):
            return "lang_mismatch"
        return None
    if lang == "en":
        if not markers:
            return "no_speech"
        if text.strip() and _has_japanese(text):
            return "lang_mismatch"
        return None
    if lang == "zh":
        if not markers:
            return "no_speech"
        # 漢字は zh/ja 共有 Unicode ブロックのため判別できないが、仮名/ハングルの
        # 混入は判定できる (§A-3 の割り切り)。
        if text.strip() and (_has_kana(text) or _has_hangul(text)):
            return "lang_mismatch"
        return None
    if lang == "ko":
        if not markers:
            return "no_speech"
        if text.strip() and not _has_hangul(text):
            return "lang_mismatch"
        return None
    return "unsupported_lang"


def expected_band(level: str | WeightLevel) -> tuple[int, int]:
    """強度レベルから期待バンド (lo, hi) を返す。

    none (0, 20) / mild (20, 45) / moderate (45, 70) / strong (70, 100)。
    """
    bands: dict[WeightLevel, tuple[int, int]] = {
        WeightLevel.NONE: (0, 20),
        WeightLevel.MILD: (20, 45),
        WeightLevel.MODERATE: (45, 70),
        WeightLevel.STRONG: (70, 100),
    }
    return bands[coerce_level(level)]


def _split_sentences(text: str) -> list[str]:
    """文を句読点・改行で分割し、空要素を除いて返す。"""
    if not text:
        return []
    parts: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch in "。．.！!？?\n":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf)
    if tail:
        parts.append(tail)
    return [s for s in parts if s.strip()]


def _normalize_ending(ending: str) -> str:
    """語尾比較用に先頭の 〜 / ~ と末尾の句読点を除去する。"""
    e = ending.strip().rstrip(_PUNCT_STRIP)
    while e and e[0] in "〜~":
        e = e[1:]
    return e


def _expand_ending_variants(endings: list[str]) -> list[str]:
    """登録語尾に丁寧語尾の活用形を決定的に追加する (metric v2 根因 1)。

    ます/です で終わる登録語尾のみ対象 (ございます → ございました/ございません 等)。
    それ以外の様式的語尾 (どす/ですわ/のじゃ…) は原形のまま照合する。
    """
    out = list(endings)
    seen = set(endings)
    for e in endings:
        for base, variants in _JA_POLITE_VARIANTS.items():
            if e.endswith(base):
                stem = e[: -len(base)]
                for v in variants:
                    cand = stem + v
                    if cand not in seen:
                        seen.add(cand)
                        out.append(cand)
    return out


def _tail_candidates(t: str) -> list[str]:
    """文末照合の候補列を返す: 原形 → 終助詞 strip (≤3) → 接続助詞 strip (≤1) → 終助詞 strip (≤2)。

    「〜おりますわ」→「〜おります」、「〜ですけれどね」→「〜ですけれど」→「〜です」の
    ように、自然な日本語の文末装飾を剥がした形でも登録語尾と照合できるようにする
    (metric v2 根因 1)。strip は候補を増やすだけで、照合は常に登録語尾との
    endswith を要求するため、無関係な語尾が新たに一致することはない。
    """
    cands = [t]
    cur = t
    for _ in range(3):
        if cur and cur[-1] in _JA_TRAIL_PARTICLES:
            cur = cur[:-1]
            cands.append(cur)
        else:
            break
    base = cands[-1]
    for conj in _JA_TRAIL_CONJUNCTIONS:
        if base.endswith(conj) and len(base) > len(conj):
            cur = base[: -len(conj)]
            cands.append(cur)
            for _ in range(2):
                if cur and cur[-1] in _JA_TRAIL_PARTICLES:
                    cur = cur[:-1]
                    cands.append(cur)
                else:
                    break
            break
    return cands


def _ends_with_any(text: str, normalized_endings: list[str]) -> bool:
    """text の文末 (句読点 strip 後) が normalized_endings のいずれかに一致するか。

    metric v2: 原形一致に加え、終助詞・接続助詞を剥がした tail 候補でも照合する
    (「ですね」「おりますわ」「ますので」を です/ます 登録で取れるように)。
    normalized_endings が空なら False。
    """
    if not normalized_endings:
        return False
    t = text.rstrip(_PUNCT_STRIP)
    for cand in _tail_candidates(t):
        if any(cand.endswith(e) for e in normalized_endings if e):
            return True
    return False


def _split_first_person_tokens(raw: str) -> list[str]:
    """first_person フィールドを照合可能な単独トークン群に分解する (metric v2 根因 3)。

    「私（わたくし）」のような読み仮名括弧付き表記を 私 / わたくし の 2 トークンに、
    「俺/オレ」のようなスラッシュ区切りを個別トークンに割る。
    """
    tokens: list[str] = []
    for part in raw.replace("（", "(").replace("）", ")").split("/"):
        part = part.strip()
        if not part:
            continue
        if "(" in part and part.endswith(")"):
            outside, _, inside = part.partition("(")
            outside = outside.strip()
            inside = inside[:-1].strip()
            if outside:
                tokens.append(outside)
            if inside:
                tokens.append(inside)
        else:
            tokens.append(part)
    return tokens


def _normalize_catchphrase_for_match(phrase: str) -> str:
    """口癖を出現カウント用に正規化する (metric v2 根因 2 の一部)。

    収録形の前後に付く省略記号・句読点 (「べ、別に……」「……来るなとは言ってない」) を
    strip し、実出力での自然な使われ方 (「べ、別に見てたわけじゃないし」) に一致させる。
    strip 後 2 文字未満になる口癖は誤ヒット源になるため照合対象から外す。
    """
    p = phrase.strip(_CATCHPHRASE_MATCH_STRIP)
    return p if len(p) >= 2 else ""


def _collect_speech_signals(
    attributes: list[dict],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """属性群から sentence_endings / lexical_markers / catchphrases / first_persons を集約する。

    語尾 (endings) / lexical_markers / first_person は speech 属性のみが対象。
    catchphrases は metric v2 から **全カテゴリ** が対象 (根因 2): ペルソナ維持は
    blend 全体の声であり、personality の口癖 (tsundere の「誰が気にするものかしら」等)
    を verbatim で使った応答が 0 点になるのは測定側の欠陥だった。
    測定可否 (skip 判定) は従来どおり speech シグナルの有無だけで決まる —
    speech 属性の無い blend は口癖があっても None のまま。
    戻り値: ``(endings, lexical_markers, catchphrases, first_persons)``。
    """
    endings: list[str] = []
    markers: list[str] = []
    catchphrases: list[str] = []
    first_persons: list[str] = []
    seen_e: set[str] = set()
    seen_m: set[str] = set()
    seen_c: set[str] = set()
    seen_fp: set[str] = set()
    for a in attributes:
        for c in a.get("catchphrases", []) or []:
            phrase = _normalize_catchphrase_for_match(normalize_catchphrase(c)["phrase"])
            if phrase and phrase not in seen_c:
                seen_c.add(phrase)
                catchphrases.append(phrase)
        if a.get("attribute_category") != "speech":
            continue
        for e in a.get("sentence_endings", []) or []:
            if not isinstance(e, str):
                continue
            ne = _normalize_ending(e)
            if ne and ne not in seen_e:
                seen_e.add(ne)
                endings.append(ne)
        for mk in a.get("lexical_markers", []) or []:
            if not isinstance(mk, str) or not mk:
                continue
            low = mk.strip().lower()
            if low and low not in seen_m:
                seen_m.add(low)
                markers.append(low)
        fp_raw = a.get("first_person") or ""
        for tok in _split_first_person_tokens(fp_raw):
            if tok not in seen_fp:
                seen_fp.add(tok)
                first_persons.append(tok)
    return endings, markers, catchphrases, first_persons


def measure_intensity(text: str, attributes: list[dict]) -> IntensityReport | None:
    """出力テキストの強度指標を採点する (metric v2, 2026-07-12)。

    speech 属性が無いブレンドは None (skip)。採点軸は (ja):
    - endings_rate    : 文末が sentence_endings に一致する割合 (0-1)。
      照合は活用展開 (ます→ました/ません…) + 終助詞/接続助詞 strip 込み。
    - catchphrase_density: catchphrases 出現数 / (文数 × _HIT_CADENCE) (0-1 クリップ)。
      口癖は全カテゴリ対象。4 文に 1 回の出現で軸満点 (毎文要求はディレクティブと矛盾)。
    - first_person_rate : 一人称トークン出現数 / (文数 × _HIT_CADENCE) (0-1 クリップ)。
      日本語は主語省略言語のため、4 文に 1 回の明示で軸満点。

    score 式 (ja):
    - endings + first_person 両方あり: 100*(0.45*endings_rate + 0.30*density + 0.25*fp_rate)
    - endings のみ              : 100*(0.60*endings_rate + 0.40*density)
    - first_person のみ         : 100*(0.60*fp_rate     + 0.40*density)

    en / zh / ko は同一の lexical_markers 経路 (A-3, sharpen-and-grow):
    100*(0.60*endings_rate + 0.40*density)  (endings_rate = marker を含む文の割合。
    zh の語気助詞・ko の語尾は文中どこでも現れうるため sentence_endings ではなく
    lexical_markers の部分一致で判定する — native zh/ko 6 属性の authoring 済み
    lexical_markers をそのまま使う)。density の cadence 正規化は ja と共通。
    band / status は verify() 側で埋める想定。

    v1 とスコアの絶対値は互換しない (v1 は上記 4 根因により実運用出力がほぼ
    0-15 点に張り付き、バンド (45-70 等) が構造的に到達不能だった)。
    """
    endings, markers, catchphrases, first_persons = _collect_speech_signals(attributes)
    lang = content_language(attributes)
    # 主シグナル: ja は語尾または一人称、en/zh/ko は lexical_markers。なければ skip。
    if lang == "ja":
        if not endings and not first_persons:
            return None
    elif lang in ("en", "zh", "ko"):
        if not markers:
            return None
    else:
        return None

    sentences = _split_sentences(text)
    sentence_count = len(sentences)

    if sentence_count == 0:
        return IntensityReport(
            score=0.0,
            endings_rate=0.0,
            catchphrase_hits=0,
            sentence_count=0,
            band=(0, 100),
            status="",
            lang=lang,
        )

    hit_denom = max(1.0, sentence_count * _HIT_CADENCE)

    if lang in ("en", "zh", "ko"):
        primary = markers
        low_sentences = [s.lower() for s in sentences]
        matching = sum(1 for s in low_sentences if any(mk in s for mk in primary))
        low_text = text.lower()
        catchphrase_hits = sum(low_text.count(c.lower()) for c in catchphrases)
        endings_rate = matching / sentence_count
        density = min(1.0, catchphrase_hits / hit_denom)
        score = 100.0 * (0.6 * endings_rate + 0.4 * density)
        return IntensityReport(
            score=score,
            endings_rate=endings_rate,
            catchphrase_hits=catchphrase_hits,
            sentence_count=sentence_count,
            band=(0, 100),
            status="",
            lang=lang,
        )

    # ja: endings + first_person の 2 または 3 軸採点
    expanded_endings = _expand_ending_variants(endings)
    matching = sum(1 for s in sentences if _ends_with_any(s, expanded_endings))
    catchphrase_hits = sum(text.count(c) for c in catchphrases)
    first_person_hits = sum(text.count(fp) for fp in first_persons)

    endings_rate = matching / sentence_count if endings else 0.0
    density = min(1.0, catchphrase_hits / hit_denom)
    fp_rate = min(1.0, first_person_hits / hit_denom)

    if endings and first_persons:
        score = 100.0 * (0.45 * endings_rate + 0.30 * density + 0.25 * fp_rate)
    elif endings:
        score = 100.0 * (0.60 * endings_rate + 0.40 * density)
    else:
        score = 100.0 * (0.60 * fp_rate + 0.40 * density)

    return IntensityReport(
        score=score,
        endings_rate=endings_rate,
        catchphrase_hits=catchphrase_hits,
        sentence_count=sentence_count,
        band=(0, 100),
        status="",
        lang=lang,
        first_person_hits=first_person_hits,
    )


def verify(
    text: str,
    attributes: list[dict],
    level: str | WeightLevel,
) -> IntensityReport | None:
    """measure_intensity にバンド比較を足し、status を確定する。

    - score < lo → "under" (警告対象。exit 0 のまま stderr に警告)
    - score > hi → "over"
    - それ以外 → "pass"

    speech 属性が無いブレンドは None。
    """
    report = measure_intensity(text, attributes)
    if report is None:
        return None
    lo, hi = expected_band(level)
    report.band = (lo, hi)
    if report.score < lo:
        report.status = "under"
    elif report.score > hi:
        report.status = "over"
    else:
        report.status = "pass"
    return report


def pre_response_check_prompt(
    names: list[str],
    weight_level: str | WeightLevel,
    last_response: str | None = None,
    lang: str = "en",
    naturalness: bool = False,
) -> str:
    """強度レベル別の「応答前自己チェックプロンプト」を返す (LLM 呼び出しなし)。

    WEIGHT_GUIDANCE、speech 属性の catchphrases 抜粋、ブレンド内の matrix conflict
    警告、および任意の last_response 反省指示を決定的に組み立てる。

    ``naturalness=True`` (§3 P2b, `docs/IMPROVEMENT_PLAN_2026-07-11_humanize.md`)
    は「人間に AI くさいと指摘された」フレーミングの自己点検節を末尾に追加する。
    リカバリループ用途: 応答生成 → `measure_naturalness` で採点 → 閾値未満なら
    この節付きプロンプトを末尾へ再注入 → 再生成 (プロンプトキャッシュの prefix を
    壊さない末尾追加。A-4/A-6 と同じ構造)。
    """
    from hersona.core.attach import load_attribute
    from hersona.core.compatibility import load_matrix

    level = coerce_level(weight_level)
    resolved_lang = lang if lang in ("en", "ja") else "en"

    band_lo, band_hi = expected_band(level)
    band = f"{band_lo}-{band_hi}"
    header = tr(
        "measure.check_prompt_header",
        resolved_lang,
        weight=level.value,
        band=band,
    )
    guidance = WEIGHT_GUIDANCE[level]
    body = _BASE_PROMPT[resolved_lang].format(weight=level.value, band=band)

    cf_lines: list[str] = []
    seen: set[str] = set()
    for name in names:
        try:
            attr = load_attribute(name)
        except KeyError:
            continue
        if attr.get("attribute_category") != "speech":
            continue
        for cp in attr.get("catchphrases", [])[:3]:
            if cp and cp not in seen:
                seen.add(cp)
                cf_lines.append(f"- {name}: {cp}")
    cf_block = ""
    if cf_lines:
        cf_block = (
            "\n"
            + tr("measure.check_prompt_catchphrases", resolved_lang)
            + "\n"
            + "\n".join(cf_lines)
        )

    matrix = load_matrix()
    conflict_lines: list[str] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if matrix.conflicts(a, b):
                conflict_lines.append(f"- {a} <-> {b}")
    conflict_block = ""
    if conflict_lines:
        conflict_block = (
            "\n"
            + tr("measure.check_prompt_conflicts", resolved_lang)
            + "\n"
            + "\n".join(conflict_lines)
        )

    reflection = ""
    if last_response is not None:
        reflection = tr("measure.check_prompt_reflection", resolved_lang) + "\n"

    naturalness_block = ""
    if naturalness:
        nat_header = tr("measure.check_prompt_naturalness_header", resolved_lang)
        nat_body = _NATURALNESS_CHECK_PROMPT[resolved_lang]
        naturalness_block = f"\n{nat_header}\n{nat_body}"

    return (
        f"{reflection}{header}\n{guidance}\n{body}{cf_block}{conflict_block}"
        f"{naturalness_block}".rstrip()
        + "\n"
    )


def format_report(report: IntensityReport, level: str | WeightLevel) -> str:
    """採点結果を CLI 1 行表示用に整形する (verify() 後専用)。"""
    lvl = coerce_level(level).value
    lo, hi = report.band
    if report.status == "pass":
        mark = tr("report.pass")
    elif report.status == "under":
        mark = tr("report.under")
    else:
        mark = tr("report.over", status=report.status)
    return tr(
        "report.line",
        score=f"{report.score:.0f}",
        endings=f"{report.endings_rate:.0%}",
        hits=report.catchphrase_hits,
        fp=report.first_person_hits,
        band=lvl,
        lo=lo,
        hi=hi,
        status=report.status,
        mark=mark,
    )
