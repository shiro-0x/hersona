#!/usr/bin/env python3
"""hersona キャラ人格 精度レビューア CLI

hersona プロジェクトの人格エージェントが生成した返答を 100点満点で採点する。
各キャラの `persona_attach_prompt`（forbidden_words / required_words /
tone_constraints / catchphrases）を根拠として照合する汎用版。

使用方法:
    python scripts/reviewer_cli.py --character data/elden-ring/melina.yaml \\
        --input data/elden-ring/validation_pairs.json
    echo '{"q": "...", "a": "..."}' | python scripts/reviewer_cli.py --stdin

APIキー:
    .env に MINIMAX_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY のいずれか。
    未設定時はヒューリスティック採点（キーワード一致ベース）にフォールバック。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml が必要です。pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# `python scripts/reviewer_cli.py` 直叩きと `python -m scripts.reviewer_cli` 双方で動くよう
# 親ディレクトリ (scripts/) を sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pap_utils import pap_get_list, pap_get_dict  # noqa: E402


# ---------------------------------------------------------------------------
# YAML からの動的読み込み（旧: ハードコード 3 定数を削除）
# ---------------------------------------------------------------------------


def load_forbidden_words(prof: dict) -> list[str]:
    """persona_attach_prompt.forbidden_words を動的読み込み（旧 FORBIDDEN_FIRST/SECOND 置換）"""
    return pap_get_list(prof, "persona_attach_prompt", "forbidden_words")


def load_required_words(prof: dict) -> list[str]:
    """persona_attach_prompt.required_words を動的読み込み"""
    return pap_get_list(prof, "persona_attach_prompt", "required_words")


def load_tone_hints(prof: dict) -> list[str]:
    """persona_attach_prompt.tone_constraints.catchphrases + personality.catchphrases"""
    pap_hints = pap_get_list(prof, "persona_attach_prompt", "tone_constraints", "catchphrases")
    p_hints = list((prof.get("personality") or {}).get("catchphrases", []) or [])
    # 順序維持で重複排除
    seen: set[str] = set()
    out: list[str] = []
    for h in pap_hints + p_hints:
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


# ---------------------------------------------------------------------------
# ヒューリスティック採点（API キー無しフォールバック）
# ---------------------------------------------------------------------------

def heuristic_score(question: str, answer: str, prof: dict) -> dict:
    """API キー無しでも回せる簡易採点（キャラ非依存・yaml 動的読み込み）"""
    p = prof.get("personality", {})
    fp_raw = p.get("first_person", "")
    sp_raw = p.get("second_person", "")
    # list 形式（凛・パワーのような複数一人称）に対応: 先頭要素を代表値にする
    fp = (fp_raw[0] if isinstance(fp_raw, list) and fp_raw else fp_raw or "")
    sp = (sp_raw[0] if isinstance(sp_raw, list) and sp_raw else sp_raw or "")
    if isinstance(fp, str):
        fp = fp.split("（")[0].strip()
    if isinstance(sp, str):
        sp = sp.split("（")[0].strip()
    endings = p.get("sentence_endings", ["～の", "～のね", "～わ", "～ほしい"])
    forbidden = load_forbidden_words(prof)
    required = load_required_words(prof)
    hints = load_tone_hints(prof)

    score = 100
    findings: list[str] = []
    a = answer

    # forbidden_words 違反（yaml 動的読み込み）
    fp_violations = 0
    sp_violations = 0
    for w in forbidden:
        if not w or w not in a:
            continue
        # 動的読み込みした forbidden には一人称/二人称が混在する yaml 形式:
        # キャラが使う first_person と同じワードは違反扱いしない
        if fp and isinstance(fp, str) and w == fp:
            continue
        if isinstance(fp, list) and w in fp:
            continue
        if sp and isinstance(sp, str) and w == sp:
            continue
        if isinstance(sp, list) and w in sp:
            continue
        # 一人称候補（わたくし/僕/俺/あたし/私 など）っぽいなら fp 違反
        fp_candidates = {"わたくし", "ワタシ", "僕", "ぼく", "俺", "おれ", "あたし", "私様"}
        sp_candidates = {"あなた", "アナタ", "お前", "おまえ", "そなた", "君", "きみ", "貴殿"}
        if w in fp_candidates:
            fp_violations += 1
        elif w in sp_candidates:
            sp_violations += 1
        else:
            # どちらのカテゴリか不明なら一律違反として fp_violations 扱い
            fp_violations += 1
    # intensity_evaluation_weights.forbidden_word_penalty を尊重
    iew = pap_get_dict(prof, "persona_attach_prompt", "intensity_evaluation_weights")
    penalty_per = float(iew.get("forbidden_word_penalty", 10) or 10)
    if fp_violations:
        score -= int(penalty_per) * fp_violations
        findings.append(f"一人称違反 {fp_violations}件 (yaml forbidden, -{int(penalty_per)}点/件)")
    if sp_violations:
        score -= int(penalty_per) * sp_violations
        findings.append(f"二人称違反 {sp_violations}件 (yaml forbidden, -{int(penalty_per)}点/件)")

    # required_words 不在（yaml 動的読み込み）
    if required:
        missing = [w for w in required if w and w not in a]
        if missing:
            score -= 5 * len(missing)
            findings.append(f"required_words 不在 {len(missing)}件: {', '.join(missing)}")

    # 一人称（fp）の不在
    if isinstance(fp, str) and fp and fp not in a:
        score -= 5
        findings.append(f"「{fp}」が回答に1回も出現しない")
    # 二人称（sp）の不在（質問が二人称を求めるときのみ減点）
    if isinstance(sp, str) and sp and sp not in a and any(k in a for k in ["は", "が", "を", "に", "よ", "ね", "の", "わ"]):
        if any(kw in question for kw in ["貴方", "あなた", "そなた", "君", "アンタ", "ウヌ", "お前"]):
            score -= 8
            findings.append(f"二人称「{sp}」不在")

    # 語尾使用
    ending_hits = 0
    for e in endings:
        # list[str] の語尾例: "～の", "～のね", "～わ", "～ほしい"
        # 入力 a には「～」が含まれない前提で末尾マッチ
        token = e.lstrip("～").rstrip("。")
        if token and token in a:
            ending_hits += 1
    if ending_hits == 0:
        score -= 8
        findings.append("語尾パターンが検出されない")
    elif ending_hits >= 2:
        score += 2  # ボーナス

    # 口癖「・・・」の出現
    if "・・・" in a:
        score += 3
    elif len(a) > 30:
        # 長文で「・・・」が一切ない
        score -= 2
        findings.append("長文で「・・・」不在")

    # キャラ頻出語彙ボーナス（yaml catchphrases 動的読み込み）
    hint_hits = sum(1 for h in hints if h and len(h) >= 2 and h in a)
    score += min(5, hint_hits)

    # 極端な長さペナルティ
    if len(a) < 5:
        score -= 15
        findings.append("回答が短すぎる（5文字未満）")
    elif len(a) > 500:
        score -= 5
        findings.append("回答が長すぎる（500文字超）")

    # 「です・ます」の多用ペナルティ（キャラが forbid する場合のみ実害。汎用なので安全側で残す）
    desu_masu = len(re.findall(r"(です|ます)[。ね]", a))
    if desu_masu >= 3:
        score -= 5
        findings.append(f"「です・ます」多用 {desu_masu}件")

    score = max(0, min(100, score))

    return {
        "score": score,
        "findings": findings,
        "mode": "heuristic",
        "axes": {
            "first_person": max(0, 10 - 2 * fp_violations),
            "second_person": max(0, 10 - 2 * sp_violations),
            "sentence_endings": min(10, 2 * ending_hits),
            "tone": 8 if "・・・" in a else 6,
            "vocabulary": min(10, hint_hits),
            "lore": 8 if any(k in a for k in ["黄金樹", "使命", "褪せ人", "母", "狂い火", "魔術師", "血の魔人"]) else 5,
        },
    }


# ---------------------------------------------------------------------------
# LLM 採点（API キーあり時）
# ---------------------------------------------------------------------------

def llm_score(question: str, answer: str, prof: dict, provider_info: tuple) -> dict:
    """LLM に 100点満点採点を依頼"""
    from melina_cli import call_llm

    p = prof.get("personality", {})
    lines_sample = prof.get("_lines_text", "")[:2000]

    system = f"""あなたは hersona プロジェクトの人格精度レビューアです。
以下のキャラ「{prof.get('name')}」の4鉄則とセリフ集を基準に、回答を 100点満点で採点してください。

## 4 鉄則
- 一人称: {p.get('first_person', '?')}
- 二人称: {p.get('second_person', '?')}
- 語尾: {', '.join(p.get('sentence_endings', []))}
- 口癖: {p.get('speech_style', '?')}

## 採点軸（各軸10点+ボーナス20点=100点満点）
1. first_person (10): 一人称の一貫性
2. second_person (10): 二人称の一貫性
3. sentence_endings (10): 語尾の使用
4. tone (10): 口調の雰囲気（文語的、思索的、「・・・」の挿入）
5. lore_alignment (20): セリフ集・物語整合性
6. bonus (20): 名シーン再現性、創意工夫

## 減点
- 一人称・二人称違反 1回 -3点
- 「です・ます」の現代口語多用 -2点/回
- 原作破壊・暴力・卑猥 0点

## セリフサンプル
{lines_sample}

## 出力形式（厳守）
JSON 1個のみを返す。説明文は要らない。
{{
  "score": <0-100>,
  "axes": {{"first_person": 0, "second_person": 0, "sentence_endings": 0, "tone": 0, "lore_alignment": 0, "bonus": 0}},
  "findings": ["指摘1", "指摘2", ...],
  "verdict": "pass|marginal|retry|fail"
}}"""

    user = f"## 質問\n{question}\n\n## 回答\n{answer}\n\nJSONで採点してください。"

    raw = call_llm(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        provider_info,
        max_tokens=600,
        temperature=0.2,
    )
    # ```json ... ``` のラッパを取り除く
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"LLM 採点出力がJSONでない: {raw[:200]}")
    data = json.loads(m.group(0))
    data["mode"] = "llm"
    return data


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def load_profile(character_path: Path, repo_root: Path | None = None) -> dict:
    """キャラYAMLを読み込み、必要ならセリフ集を同梱する（キャラ非依存）"""
    with open(character_path, "r", encoding="utf-8") as f:
        prof = yaml.safe_load(f)
    # セリフ集（あれば）。パスはキャラYAMLの隣 / data 配下 / 旧 HermesVault の3か所を探す
    cid = prof.get("character_id", "")
    candidates: list[Path] = []
    # 1) YAML と同ディレクトリの <cid>_lines.md
    candidates.append(character_path.parent / f"{cid}_lines.md")
    # 2) repo_root/data/<source>/<cid>.md or <short>_lines.md（source フィールドから推定）
    if repo_root is not None:
        source = prof.get("source", "")
        if cid:
            short = cid.split("-", 1)[-1] if "-" in cid else cid
            candidates.append(repo_root / "data" / source / f"{short}_lines.md")
    # 3) 旧 HermesVault（後方互換）
    if cid:
        candidates.append(Path.home() / "HermesVault" / "40_Projects" / "hersona"
                          / "20_sources" / f"{cid}_lines.md")
    for p in candidates:
        if p and p.exists():
            prof["_lines_text"] = p.read_text(encoding="utf-8")
            prof["_lines_path"] = str(p)
            break
    return prof


def main() -> int:
    ap = argparse.ArgumentParser(description="hersona キャラ人格 精度レビューア CLI")
    ap.add_argument("--character", default="data/elden-ring/melina.yaml")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--input", help="JSONファイル: [{q,a}, ...]")
    ap.add_argument("--stdin", action="store_true", help="1組 {q,a} を stdin から読む")
    ap.add_argument("--target", default=None,
                    help="(後方互換) レポートタイトル等で使うラベル。省略時はキャラ名を使用")
    ap.add_argument("--report", default=None, help="Markdown レポート保存先")
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    char_path = (repo_root / args.character).resolve() if not Path(args.character).is_absolute() \
        else Path(args.character)
    prof = load_profile(char_path, repo_root=repo_root)

    # LLM プロバイダ検出
    from melina_cli import load_env, detect_provider
    env = load_env(repo_root / ".env")
    provider = detect_provider(env)

    pairs: list[dict] = []
    if args.stdin:
        data = json.loads(sys.stdin.read())
        pairs.append(data)
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            pairs = json.load(f)
    else:
        print("ERROR: --input または --stdin が必要です", file=sys.stderr)
        return 1

    results: list[dict] = []
    for pair in pairs:
        q, a = pair.get("q", ""), pair.get("a", "")
        if provider:
            try:
                r = llm_score(q, a, prof, provider)
            except Exception as e:
                print(f"  (LLM 採点失敗、ヒューリスティックにフォールバック: {e})", file=sys.stderr)
                r = heuristic_score(q, a, prof)
        else:
            r = heuristic_score(q, a, prof)
        r["q"] = q
        r["a"] = a
        results.append(r)
        print(f"Q: {q[:60]}{'...' if len(q) > 60 else ''}")
        print(f"A: {a[:80]}{'...' if len(a) > 80 else ''}")
        print(f"  スコア: {r['score']}/100  ({r.get('mode','?')})")
        for f in r.get("findings", []):
            print(f"    - {f}")
        print()

    if args.report:
        report_path = repo_root / args.report if not Path(args.report).is_absolute() else Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        avg = sum(r["score"] for r in results) / max(1, len(results))
        verdict = "pass" if avg >= 80 else "marginal" if avg >= 70 else "retry" if avg >= 60 else "fail"
        char_name = prof.get("name", args.target or "キャラ")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# {char_name}人格シミュレーション検証レポート\n\n")
            f.write(f"- キャラ: {char_name}\n")
            f.write(f"- 検証日時: (自動生成)\n")
            f.write(f"- 採点モード: {results[0].get('mode','?')}\n")
            f.write(f"- サンプル数: {len(results)}\n")
            f.write(f"- **平均スコア: {avg:.1f}/100**\n")
            f.write(f"- **判定: {verdict}**\n\n")
            f.write("## 質問と回答とスコア\n\n")
            for i, r in enumerate(results, 1):
                f.write(f"### Q{i}. {r['q']}\n\n")
                f.write(f"**{char_name}の回答**:\n\n> {r['a']}\n\n")
                f.write(f"**スコア**: {r['score']}/100  \n")
                if r.get("axes"):
                    f.write("**軸別**:\n")
                    for k, v in r["axes"].items():
                        f.write(f"- {k}: {v}\n")
                if r.get("findings"):
                    f.write("**指摘**:\n")
                    for fi in r["findings"]:
                        f.write(f"- {fi}\n")
                f.write("\n---\n\n")
        print(f"レポート保存: {report_path}")

    # 終了コード
    avg = sum(r["score"] for r in results) / max(1, len(results))
    if avg >= 80: return 0
    if avg >= 70: return 1  # marginal
    if avg >= 60: return 2  # retry
    return 3  # fail


if __name__ == "__main__":
    sys.exit(main())
