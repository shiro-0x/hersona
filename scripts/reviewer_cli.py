#!/usr/bin/env python3
"""メリーナ返答 精度レビューア CLI

メリーナ人格エージェントが生成した返答を 100点満点で採点する。
`melina_lines.md` のセリフと `melina.yaml` の 4鉄則 を根拠として照合。

使用方法:
    python scripts/reviewer_cli.py --target melina --report data/elden-ring/validation_report.md
    python scripts/reviewer_cli.py --input data/elden-ring/validation_pairs.json
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

# メリーナ絶対禁止ワード（4鉄則違反の即時減点対象）
FORBIDDEN_FIRST = ["わたくし", "ワタシ", "僕", "ぼく", "俺", "おれ", "あたし", "私様"]
FORBIDDEN_SECOND = ["あなた", "アナタ", "お前", "おまえ", "そなた", "君", "きみ", "貴殿"]

# メリーナ頻出語彙（加点要素）
MELINA_HINTS = ["黄金樹", "褪せ人", "使命", "導く", "母", "祝福", "ルーン", "契約", "霊", "・・・", "貴方", "私", "私にも"]


# ---------------------------------------------------------------------------
# ヒューリスティック採点（API キー無しフォールバック）
# ---------------------------------------------------------------------------

def heuristic_score(question: str, answer: str, prof: dict) -> dict:
    """API キー無しでも回せる簡易採点"""
    p = prof.get("personality", {})
    fp = p.get("first_person", "私").split("（")[0].strip()
    sp = p.get("second_person", "貴方").split("（")[0].strip()
    endings = p.get("sentence_endings", ["～の", "～のね", "～わ", "～ほしい"])

    score = 100
    findings: list[str] = []
    a = answer

    # 一人称違反
    fp_violations = sum(1 for w in FORBIDDEN_FIRST if w in a and w != fp and not a.startswith(fp))
    if fp_violations:
        score -= 10 * fp_violations
        findings.append(f"一人称違反 {fp_violations}件")
    if fp and fp not in a:
        score -= 5
        findings.append(f"「{fp}」が回答に1回も出現しない")

    # 二人称違反
    sp_violations = sum(1 for w in FORBIDDEN_SECOND if w in a and w != sp)
    if sp_violations:
        score -= 10 * sp_violations
        findings.append(f"二人称違反 {sp_violations}件")
    if sp and sp not in a and any(k in a for k in ["は", "が", "を", "に", "よ", "ね", "の", "わ"]):
        # 二人称が必要な文脈（相手への呼びかけ）の場合のみ減点
        if any(kw in question for kw in ["貴方", "あなた", "そなた", "君"]):
            score -= 8
            findings.append(f"二人称「{sp}」不在")

    # 語尾使用
    ending_hits = sum(1 for e in endings if e.lstrip("～") in a)
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

    # メリーナ語彙ボーナス
    hint_hits = sum(1 for h in MELINA_HINTS if h in a)
    score += min(5, hint_hits)

    # 極端な長さペナルティ
    if len(a) < 5:
        score -= 15
        findings.append("回答が短すぎる（5文字未満）")
    elif len(a) > 500:
        score -= 5
        findings.append("回答が長すぎる（500文字超）")

    # 「です・ます」の多用ペナルティ
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
            "first_person": 10 - 2 * fp_violations,
            "second_person": 10 - 2 * sp_violations,
            "sentence_endings": min(10, 2 * ending_hits),
            "tone": 8 if "・・・" in a else 6,
            "vocabulary": min(10, hint_hits),
            "lore": 8 if any(k in a for k in ["黄金樹", "使命", "褪せ人", "母"]) else 5,
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

def load_profile(character_path: Path) -> dict:
    with open(character_path, "r", encoding="utf-8") as f:
        prof = yaml.safe_load(f)
    # セリフ集も読み込む（ヒューリスティック用）
    cid = prof.get("character_id", "")
    if cid.startswith("elden-ring-"):
        lines_path = (Path.home() / "HermesVault" / "40_Projects" / "hersona"
                      / "20_sources" / "elden-ring" / f"{cid.replace('elden-ring-', '')}_lines.md")
        if lines_path.exists():
            prof["_lines_text"] = lines_path.read_text(encoding="utf-8")
    return prof


def main() -> int:
    ap = argparse.ArgumentParser(description="メリーナ返答 精度レビューア CLI")
    ap.add_argument("--character", default="data/elden-ring/melina.yaml")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--input", help="JSONファイル: [{q,a}, ...]")
    ap.add_argument("--stdin", action="store_true", help="1組 {q,a} を stdin から読む")
    ap.add_argument("--target", default="melina")
    ap.add_argument("--report", default=None, help="Markdown レポート保存先")
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    char_path = (repo_root / args.character).resolve() if not Path(args.character).is_absolute() \
        else Path(args.character)
    prof = load_profile(char_path)

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
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# メリーナ人格シミュレーション検証レポート\n\n")
            f.write(f"- キャラ: {prof.get('name')}\n")
            f.write(f"- 検証日時: (自動生成)\n")
            f.write(f"- 採点モード: {results[0].get('mode','?')}\n")
            f.write(f"- サンプル数: {len(results)}\n")
            f.write(f"- **平均スコア: {avg:.1f}/100**\n")
            f.write(f"- **判定: {verdict}**\n\n")
            f.write("## 質問と回答とスコア\n\n")
            for i, r in enumerate(results, 1):
                f.write(f"### Q{i}. {r['q']}\n\n")
                f.write(f"**メリーナの回答**:\n\n> {r['a']}\n\n")
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
