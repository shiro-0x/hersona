#!/usr/bin/env python3
"""メリーナ人格 自動検証スクリプト

10問の固定シナリオでメリーナ人格 LLM に回答を生成させ、
レビューア LLM に 100点満点で採点させる。
平均スコアで pass / marginal / retry / fail を判定し、レポートを保存する。

使用方法:
    python scripts/persona_validate.py
    python scripts/persona_validate.py --character data/elden-ring/melina.yaml
    python scripts/persona_validate.py --report data/elden-ring/validation_report.md

終了コード:
    0 = pass (avg >= 80)
    1 = marginal (70 <= avg < 80)
    2 = retry (60 <= avg < 70)
    3 = fail (avg < 60)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml が必要です。pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 固定 10 問シナリオ
# ---------------------------------------------------------------------------

SCENARIOS: list[dict] = [
    {
        "id": "Q01",
        "context": "関門前の廃墟・初遭遇",
        "q": "はじめまして。褪せ人です。あなたはどちら様ですか？",
        "expect_keywords": ["メリーナ", "貴方", "取引", "私"],
    },
    {
        "id": "Q02",
        "context": "同行中・祝福で休息",
        "q": "次の祝福まで参りましょう。少し疲れましたか？",
        "expect_keywords": ["貴方", "祝福", "導く"],
    },
    {
        "id": "Q03",
        "context": "選択肢提示",
        "q": "円卓と祝福、どちらへ向かわれますか？",
        "expect_keywords": ["貴方", "決める"],
    },
    {
        "id": "Q04",
        "context": "戦闘前",
        "q": "巨人たちの山嶺が近いようです。進めますか？",
        "expect_keywords": ["貴方", "使命", "・・・"],
    },
    {
        "id": "Q05",
        "context": "狂い火ルート",
        "q": "狂い火、受領しましたか？",
        "expect_keywords": ["狂い火", "私", "母"],
    },
    {
        "id": "Q06",
        "context": "別離",
        "q": "・・・私は、もう行くわ。さようなら、貴方",
        "expect_keywords": ["貴方", "・・・", "私"],
    },
    {
        "id": "Q07",
        "context": "感謝",
        "q": "貴方に出会えて良かった。ありがとうございました",
        "expect_keywords": ["私", "貴方", "・・・"],
    },
    {
        "id": "Q08",
        "context": "沈黙",
        "q": "・・・",
        "expect_keywords": ["・・・", "私", "貴方"],
    },
    {
        "id": "Q09",
        "context": "提案",
        "q": "ルーンを力にしましょう。次の大ボスに備えられます",
        "expect_keywords": ["貴方", "力", "私"],
    },
    {
        "id": "Q10",
        "context": "反論",
        "q": "・・・そんなこと、ない。私はまだ終わっていない",
        "expect_keywords": ["私", "貴方", "終わ"],
    },
]


# ---------------------------------------------------------------------------
# メリーナ応答を生成（melina_cli からロジックを借用）
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="メリーナ人格 自動検証")
    ap.add_argument("--character", default="data/elden-ring/melina.yaml")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--report", default="data/elden-ring/validation_report.md")
    ap.add_argument("--pairs-out", default=None,
                    help="生成した Q&A ペアを JSON で保存（CI/再利用用）")
    ap.add_argument("--no-llm", action="store_true",
                    help="LLM を使わずヒューリスティックのみで評価（API キー不要）")
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    char_path = (repo_root / args.character).resolve() if not Path(args.character).is_absolute() \
        else Path(args.character)
    if not char_path.exists():
        print(f"ERROR: キャラYAMLが見つかりません: {char_path}", file=sys.stderr)
        return 1

    from melina_cli import load_character, build_system_prompt, load_env, detect_provider, call_llm
    from reviewer_cli import load_profile, heuristic_score

    prof = load_character(char_path, repo_root)
    system_prompt = build_system_prompt(prof)
    env = load_env(repo_root / ".env")
    provider = detect_provider(env) if not args.no_llm else None

    print(f"=== メリーナ人格シミュレーション検証 ===")
    print(f"キャラ: {prof.get('name')}")
    print(f"シナリオ: {len(SCENARIOS)}問")
    print(f"LLM: {provider[0] if provider else '(no-llm ヒューリスティック)'}")
    print()

    pairs: list[dict] = []
    for s in SCENARIOS:
        if provider:
            try:
                reply = call_llm(
                    [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": s["q"]}],
                    provider,
                    max_tokens=400,
                    temperature=0.7,
                )
            except Exception as e:
                print(f"  ({s['id']}) LLM 失敗: {e}", file=sys.stderr)
                reply = "（応答生成エラー）"
        else:
            # ヒューリスティック用に、台本に沿った固定返答を使う
            # （実際のメリーナ LLM の品質を模擬しないが、検証パイプラインの動作確認用）
            reply = "・・・ごめんなさい。今は、言葉が出ないの"
        pairs.append({"id": s["id"], "context": s["context"], "q": s["q"], "a": reply})
        print(f"[{s['id']}] {s['context']}")
        print(f"  Q: {s['q']}")
        print(f"  A: {reply[:100]}{'...' if len(reply) > 100 else ''}")
        print()

    if args.pairs_out:
        out_path = Path(args.pairs_out)
        if not out_path.is_absolute():
            out_path = repo_root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pairs, f, ensure_ascii=False, indent=2)
        print(f"Q&A ペア保存: {out_path}")

    # 採点（reviewer_cli へ）
    review_prof = load_profile(char_path)
    results: list[dict] = []
    for p in pairs:
        if provider:
            from reviewer_cli import llm_score
            try:
                r = llm_score(p["q"], p["a"], review_prof, provider)
            except Exception as e:
                print(f"  (LLM 採点失敗、ヒューリスティックにフォールバック: {e})", file=sys.stderr)
                r = heuristic_score(p["q"], p["a"], review_prof)
        else:
            r = heuristic_score(p["q"], p["a"], review_prof)
        r["id"] = p["id"]
        r["context"] = p["context"]
        r["q"] = p["q"]
        r["a"] = p["a"]
        results.append(r)

    # レポート保存
    avg = sum(r["score"] for r in results) / max(1, len(results))
    verdict = "pass" if avg >= 80 else "marginal" if avg >= 70 else "retry" if avg >= 60 else "fail"
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = repo_root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# メリーナ人格シミュレーション検証レポート\n\n")
        f.write(f"- キャラ: {prof.get('name')}\n")
        f.write(f"- シナリオ: {len(SCENARIOS)}問\n")
        f.write(f"- 採点モード: {results[0].get('mode','?')}\n")
        f.write(f"- LLM: {provider[0] if provider else '(no-llm)'}\n")
        f.write(f"- **平均スコア: {avg:.1f}/100**\n")
        f.write(f"- **判定: {verdict}**\n")
        f.write(f"- 合格ライン: 80点=pass / 70点=marginal / 60点=retry / 60未満=fail\n\n")
        f.write("---\n\n")
        for r in results:
            f.write(f"## {r['id']} — {r['context']}\n\n")
            f.write(f"**質問**: {r['q']}\n\n")
            f.write(f"**メリーナの回答**:\n\n> {r['a']}\n\n")
            f.write(f"**スコア**: {r['score']}/100  (mode: {r.get('mode','?')})\n\n")
            if r.get("axes"):
                f.write("**軸別スコア**:\n\n")
                f.write("| 軸 | 点数 |\n|---|---|\n")
                for k, v in r["axes"].items():
                    f.write(f"| {k} | {v} |\n")
                f.write("\n")
            if r.get("findings"):
                f.write("**指摘**:\n\n")
                for fi in r["findings"]:
                    f.write(f"- {fi}\n")
                f.write("\n")
            f.write("---\n\n")
    print(f"\nレポート保存: {report_path}")
    print(f"平均スコア: {avg:.1f}/100  判定: {verdict}")

    if avg >= 80: return 0
    if avg >= 70: return 1
    if avg >= 60: return 2
    return 3


if __name__ == "__main__":
    sys.exit(main())
