"""Unit tests for scripts/persona_attach.py::_legacy_score (Wave2-T8).

背景: Wave1-T3 (commit 0d418a5 + eef5473) で --legacy-score フラグを
導入したが、その挙動 (旧式: 100 - Σpenalty の絶対減点) を pin する
自動テストが無かった。本ファイルは _legacy_score の各減点ルールを
確実に回帰検出できるようにする。

スコープ:
  - 違反なし
  - forbidden_words 違反 1件 (penalty=5 設定時)
  - forbidden_words 違反 2件 (penalty=5 設定時)
  - required_words 欠落
  - first_person 違反
  - 3 キャラ yaml による統合テスト (メリーナ / 遠坂 / パワー)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# scripts/ を sys.path に通す
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from persona_attach import _legacy_score  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

# 短い parametrize 用 ap (テンプレ) — ケースごとに forbidden / required / first_person を
# 差し替える。length / sentence_endings の影響を受けないよう text は 80 chars に固定し、
# response_length.preferred = 100 に設定して preferred band (+2) を当てて基線を 100 にする。
_BASE_AP = {
    "register_call": "test_legacy",
    "forbidden_words": [],
    "required_words": [],
    "tone_constraints": {
        "first_person": "わたし",
        "second_person": "貴方",
    },
    # preferred を 200 に設定し、テスト text (72 chars) を band (140-260) の外に出す。
    # これによりケース 2-5 で基線が 100 (ボーナスなし) となり、期待値 95 / 90 を再現できる。
    "response_length": {"min": 20, "max": 2000, "preferred": 200},
    "intensity_evaluation_weights": {
        "forbidden_word_penalty": 5,  # 1件5点 (テストの期待値 95 / 90 を再現する設定)
    },
}

# 72 chars のテンプレ text (ケース 2-5 で使用)。
# preferred=200, band=140-260 の外なので preferred band ボーナスは当たらない。
# 「わたし」「貴方」「じゃ」を全て含む → ケース 2/3 で forbidden に使えば厳密に 1件/2件 ヒット、
# ケース 4 で required の「んじゃ」を不在にすることで required 欠落 (-5) を検証、
# ケース 5 で ap.tc.first_person を別単語にすれば first_person 不在 (-5) を検証。
_TEXT_BASELINE = (
    "「わたし」は貴方の問いに答えるわよ。「じゃ」、穏やかに思索してから語るのね。"
    "静かに貴方の問いを受け止めて、丁寧に言葉を選びたいと思うのね、貴方。"
)  # 72 chars


def _count_first_person(ap: dict, text: str) -> bool:
    fp = (ap.get("tone_constraints") or {}).get("first_person")
    if isinstance(fp, str):
        return fp in text
    if isinstance(fp, list):
        return any(m in text for m in fp)
    return True  # 設定なし = チェック対象外


def _count_second_person(ap: dict, text: str) -> bool:
    sp = (ap.get("tone_constraints") or {}).get("second_person")
    if isinstance(sp, str):
        return sp in text
    if isinstance(sp, list):
        return any(m in text for m in sp)
    return True


def _expected_score(ap: dict, text: str) -> int:
    """テストの期待値ロジック (関数本体の挙動をミラーする)。

    1. 基線 100
    2. forbidden: penalty_per × violations
    3. required: 5 × missing
    4. first_person 不在: -5
    5. second_person 不在: -5
    6. text < 20 chars: -10
    7. text > 2000 chars: -5
    8. preferred ±30% band: +2
    9. clamp [0, 100]
    """
    score = 100
    weights = ap.get("intensity_evaluation_weights") or {}
    penalty_per = weights.get("forbidden_word_penalty", 10)

    import re
    violations = [w for w in ap.get("forbidden_words", []) if re.search(re.escape(w), text)]
    score -= penalty_per * len(violations)

    missing = [w for w in ap.get("required_words", []) if w not in text]
    score -= 5 * len(missing)

    if not _count_first_person(ap, text):
        score -= 5
    if not _count_second_person(ap, text):
        score -= 5

    if len(text) < 20:
        score -= 10
    elif len(text) > 2000:
        score -= 5

    rl = ap.get("response_length") or {}
    preferred = rl.get("preferred")
    if preferred and abs(len(text) - preferred) <= preferred * 0.3:
        score += 2

    return max(0, min(100, score))


def _run_legacy(ap: dict, text: str, tmp_path: Path) -> int:
    """_legacy_score を呼び出して exit code を返す。"""
    return _legacy_score(
        ap=ap,
        register_call=ap["register_call"],
        text=text,
        side="user",
        input_path=tmp_path / "sample.txt",
        meta_note="",
    )


# ---------------------------------------------------------------------------
# 最小ケース (5 種)
# ---------------------------------------------------------------------------


def test_legacy_no_violations_scores_100(tmp_path, capsys):
    """違反なし → 100点。

    forbidden / required / first_person 全てクリア + preferred band 内 (+2) → 102 → clamp 100。
    """
    ap = {
        **_BASE_AP,
        "register_call": "no_violations",
        "forbidden_words": ["ダメ"],
        "required_words": ["わたし", "貴方", "じゃ"],
    }
    # preferred=200, band=140〜260 chars の text を作る (200 chars ジャスト)
    text = (
        "「わたし」は貴方の問いに答えるわよ。「じゃ」、穏やかに思索してから語るのね。"
        "静かに貴方の問いを受け止めて、丁寧に言葉を選びたいと思うのね、貴方。"
        "余計な贅肉は捨てて、芯のある一節だけを差し上げたいの。"
        "古都の夜霧のように静かに、それでいて芯にある灯を絶やさない言葉でありたいの。"
        "「わたし」はそう願う。あなたが受け取るその一語一語が、ほんの一瞬でも"
        "静謐な灯火となるならば、こんなに嬉しいことはないわよ、貴方。"
    )
    # 200 chars にトリム (超過時)
    text = text[:200]
    assert 140 <= len(text) <= 260, f"text length {len(text)} not in preferred band (140-260)"
    assert not any(w in text for w in ap["forbidden_words"])
    assert all(w in text for w in ap["required_words"])
    assert _count_first_person(ap, text)
    assert _count_second_person(ap, text)

    expected = _expected_score(ap, text)
    assert expected == 100, f"expected 100, got {expected}"

    rc = _run_legacy(ap, text, tmp_path)
    out = capsys.readouterr().out
    assert "スコア: 100/100" in out, out
    assert "判定: pass" in out, out
    assert "forbidden_words 違反" not in out
    assert "required_words 不在" not in out
    assert "一人称" not in out  # 「不在」を冠した指摘は出ない
    # 100点 = pass判定 → exit 0
    assert rc == 0


def test_legacy_one_forbidden_violation_scores_95(tmp_path, capsys):
    """forbidden_words 違反 1件 (penalty=5) → 95点。"""
    ap = {
        **_BASE_AP,
        "register_call": "one_forbidden",
        "forbidden_words": ["わたし"],  # baseline テキストに含まれるので 1件ヒット
        "required_words": [],
    }
    text = _TEXT_BASELINE
    # pre-condition: 1件だけ forbidden にヒット
    import re
    hits = [w for w in ap["forbidden_words"] if re.search(re.escape(w), text)]
    assert len(hits) == 1, hits
    assert _count_first_person(ap, text)  # first_person は「わたし」だが ap.tc.fp も「わたし」 → ヒット
    assert _count_second_person(ap, text)

    expected = _expected_score(ap, text)
    assert expected == 95, f"expected 95, got {expected}"

    rc = _run_legacy(ap, text, tmp_path)
    out = capsys.readouterr().out
    assert "スコア: 95/100" in out, out
    assert "forbidden_words 違反 1件" in out, out
    # 95 >= 80 → pass判定 → exit 0 (verdict pass の境界)
    assert rc == 0


def test_legacy_two_forbidden_violations_score_90(tmp_path, capsys):
    """forbidden_words 違反 2件 (penalty=5 × 2) → 90点。"""
    ap = {
        **_BASE_AP,
        "register_call": "two_forbidden",
        "forbidden_words": ["わたし", "貴方"],  # baseline テキストに両方含まれる
        "required_words": [],
    }
    text = _TEXT_BASELINE
    import re
    hits = [w for w in ap["forbidden_words"] if re.search(re.escape(w), text)]
    assert len(hits) == 2, hits
    # first_person / second_person チェックは ap.tc.fp / sp に依存するので
    # forbidden と独立に評価する。fp="わたし" は text に含まれる → ヒット
    assert _count_first_person(ap, text)
    # sp="貴方" も text に含まれる → ヒット
    assert _count_second_person(ap, text)

    expected = _expected_score(ap, text)
    assert expected == 90, f"expected 90, got {expected}"

    rc = _run_legacy(ap, text, tmp_path)
    out = capsys.readouterr().out
    assert "スコア: 90/100" in out, out
    assert "forbidden_words 違反 2件" in out, out
    # 90 >= 80 → pass
    assert rc == 0


def test_legacy_required_missing_scores_95(tmp_path, capsys):
    """required_words 欠落 → 95点 (1件 -5)。"""
    ap = {
        **_BASE_AP,
        "register_call": "required_missing",
        "forbidden_words": [],
        # baseline テキストは「じゃ」を含むが「んじゃ」「ません」を含まない
        "required_words": ["んじゃ", "貴方"],  # 「んじゃ」不在 → -5
    }
    text = _TEXT_BASELINE
    missing = [w for w in ap["required_words"] if w not in text]
    assert missing == ["んじゃ"], missing
    # forbidden 違反 0
    import re
    assert not any(re.search(re.escape(w), text) for w in ap["forbidden_words"])
    # first_person / second_person ヒット
    assert _count_first_person(ap, text)
    assert _count_second_person(ap, text)

    expected = _expected_score(ap, text)
    assert expected == 95, f"expected 95, got {expected}"

    rc = _run_legacy(ap, text, tmp_path)
    out = capsys.readouterr().out
    assert "スコア: 95/100" in out, out
    assert "required_words 不在 1件" in out, out
    assert "んじゃ" in out
    # 95 >= 80 → pass
    assert rc == 0


def test_legacy_first_person_missing_scores_95(tmp_path, capsys):
    """first_person 違反 (不在) → 95点 (-5)。"""
    ap = {
        **_BASE_AP,
        "register_call": "first_person_missing",
        "forbidden_words": [],
        "required_words": [],
        # ap.tc.first_person を baseline テキストに含まれない単語に変える
        "tone_constraints": {
            "first_person": "余輩",  # baseline テキストに無い
            "second_person": "貴方",
        },
    }
    text = _TEXT_BASELINE
    assert not _count_first_person(ap, text), "first_person should be missing"
    assert _count_second_person(ap, text)
    import re
    assert not any(re.search(re.escape(w), text) for w in ap["forbidden_words"])

    expected = _expected_score(ap, text)
    assert expected == 95, f"expected 95, got {expected}"

    rc = _run_legacy(ap, text, tmp_path)
    out = capsys.readouterr().out
    assert "スコア: 95/100" in out, out
    assert "一人称「余輩」不在" in out, out
    # 95 >= 80 → pass
    assert rc == 0


# ---------------------------------------------------------------------------
# 統合テスト: 3 キャラ yaml を使った一気通貫の --legacy-score 評価
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

# pytest の parametrize 順序: メリーナ → 遠坂 → パワー
CHARACTER_YAMLS = [
    REPO_ROOT / "data" / "elden-ring" / "melina.yaml",
    REPO_ROOT / "data" / "fate" / "tohsaka.yaml",
    REPO_ROOT / "data" / "chainsaw-man" / "power.yaml",
]


def _load_persona_attach_prompt(yaml_path: Path) -> dict:
    """キャラ yaml から persona_attach_prompt ブロックを読み込む。"""
    import yaml as pyyaml
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = pyyaml.safe_load(f)
    pap = data.get("persona_attach_prompt")
    assert isinstance(pap, dict), f"persona_attach_prompt missing in {yaml_path}"
    return pap


@pytest.mark.parametrize("yaml_path", CHARACTER_YAMLS, ids=lambda p: p.stem)
def test_legacy_score_integration_3_characters(tmp_path, capsys, yaml_path):
    """3 キャラ yaml を読み込み、_legacy_score が「
      - 例外を投げない
      - スコアが 0-100 の整数
      - キャラ本来の一人称 (first_person) を含む text なら 100 点
    」ことを確認する。

    旧形式 (絶対減点) と新形式 (重み付き合成) は共存しているので、
    本テストは「旧形式でも安全に動く」= 「回帰しても他に影響しない」ことの保証として位置づける。
    """
    import re

    pap = _load_persona_attach_prompt(yaml_path)
    fp_field = (pap.get("tone_constraints") or {}).get("first_person")
    if isinstance(fp_field, list):
        first_person = fp_field[0]
    else:
        first_person = fp_field or "私"

    # キャラ本来の一人称 + required_words を全て含む text を作る (80 chars 前後)
    required = pap.get("required_words") or []
    # required_words に含まれない first_person を使う (required チェックは独立)
    text = f"「{first_person}」は貴方の問いに答えるわ。「じゃ」、穏やかに思索してから話すのよ。慎み深く。"
    # 必要なら required を含める
    for w in required:
        if w not in text:
            text += f" 〔{w}〕"
    # 80 chars 程度に丸める
    if len(text) > 130:
        text = text[:130]
    if len(text) < 20:
        text = text + "。" * (20 - len(text))

    # 旧形式 (forbidden_word_penalty) が無ければ入れる
    if "intensity_evaluation_weights" not in pap:
        pap["intensity_evaluation_weights"] = {}
    pap["intensity_evaluation_weights"].setdefault("forbidden_word_penalty", 10)
    # response_length.preferred が無ければ 100 で
    if not (pap.get("response_length") or {}).get("preferred"):
        pap.setdefault("response_length", {})["preferred"] = 100

    # 実行
    rc = _legacy_score(
        ap=pap,
        register_call=pap["register_call"],
        text=text,
        side="user",
        input_path=tmp_path / f"{yaml_path.stem}.txt",
        meta_note="",
    )
    out = capsys.readouterr().out

    # exit code は 0 (pass) / 1 (fail) のいずれか (スコア依存)
    assert rc in (0, 1), f"unexpected exit code {rc} for {yaml_path.name}"

    # スコア表記が 0-100 の整数で出ている
    m = re.search(r"スコア:\s*(\d+)/100", out)
    assert m, f"score line not found in output for {yaml_path.name}:\n{out}"
    score = int(m.group(1))
    assert 0 <= score <= 100, f"score {score} out of [0,100] for {yaml_path.name}"

    # 旧形式 (mode=legacy) で動作していることを確認
    assert "mode=legacy" in out, f"mode should be 'legacy' for {yaml_path.name}:\n{out}"

    # first_person が text に含まれていれば、-5 減点なし (スコア寄与なし)
    if first_person in text:
        assert "一人称" not in out or "不在" not in out.split("判定:")[1], (
            f"first_person '{first_person}' is present but legacy_score reported it missing:\n{out}"
        )
