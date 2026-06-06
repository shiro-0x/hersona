#!/usr/bin/env python3
"""few-shot レビュー用: example_dialogues を 1 ターンずつ抽出し、レビュー観点を提示する。

使用方法:
    python3 scripts/review_fewshot.py melina
    python3 scripts/review_fewshot.py toh
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
TARGETS = {
    "melina": "data/elden-ring/melina.yaml",
    "toh": "data/fate/tohsaka.yaml",
}

REVIEW_POINTS = [
    "1人称/2人称レジスター: 宣言通りか（メリーナ: 私/貴方、凛: わたし/あたし × 貴方/アンタ）",
    "口癖・決め台詞: 必要数出ているか（『殺すわよ』『心の贅肉よ』『狂い火に向かっては、いけない』など）",
    "語尾: catchphrases/sentence_endings に合致するか（凛: ～わ・～のよ・～わよ、メリーナ: ～の・～わ・～ほしい）",
    "キャラの角: ツンデレ・姉・魔術師（凛）／静謐・使命・導きの厳格さ（メリーナ）がちゃんと立っているか",
    "運用ルール抵触: メタ発言（『ロールプレイ的に』『キャラとして』）、二人称連発、口癖連発がないか",
    "forbidden_words 違反: assistant 側に『僕』『俺』『わたくし』『お前』等が出てないか（user 側はOK）",
    "required_words 充足: メリーナ: 私・貴方・・・・、凛: わたし・貴方・アンタ・心の贅肉 が含まれるか",
    "response_length.preferred ±30%: メリーナ 80字、凛 100字 に近いか",
    "user 側の自然さ: テストの踏み台として成立するか（キャラになりきりすぎず、テスト入力として機能するか）",
]


def review(name: str, path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    ap = data["persona_attach_prompt"]
    examples = ap.get("example_dialogues") or []

    print(f"=== {name} ({path}) ===")
    print(f"character:  {ap.get('name')}")
    print(f"schema:     {ap.get('schema_version')}")
    print(f"examples:   {len(examples)} ターン")
    print(f"first_person:     {ap.get('tone_constraints', {}).get('first_person')}")
    print(f"second_person:    {ap.get('tone_constraints', {}).get('second_person')}")
    print(f"required_words:   {ap.get('required_words')}")
    print(f"forbidden_words:  {ap.get('forbidden_words')}")
    print(f"response_length:  {ap.get('response_length')}")
    print()

    for i, ex in enumerate(examples, 1):
        u = ex.get("user", "")
        a = ex.get("assistant", "")
        ctx = ex.get("context", "")
        print(f"--- ターン {i} ({len(a)} chars) ---")
        if ctx:
            print(f"context: {ctx}")
        print(f"  user:      {u}")
        print(f"  assistant: {a}")
        print()

    print("=== レビュー観点（運用ルール準拠の確認） ===")
    for p in REVIEW_POINTS:
        print(f"  - {p}")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in TARGETS:
        print(f"使用方法: {sys.argv[0]} {'|'.join(TARGETS.keys())}")
        return 1
    name = sys.argv[1]
    review(name, REPO_ROOT / TARGETS[name])
    return 0


if __name__ == "__main__":
    sys.exit(main())
