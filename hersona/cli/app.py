"""hersona CLI 本体 (argparse)。

サブコマンド:
    hersona list                       利用可能な属性を一覧
    hersona show <name>                属性の詳細
    hersona matrix [--json]            相性マトリクスをダンプ
    hersona blend <name> [<name>...]   属性をブレンドしてプロンプト注入ブロックを表示
    hersona recommend [--answers ...]  診断クイズ → 推薦 (→ --apply で注入ブロック)
    hersona create [...]               属性を作成しユーザー名前空間に保存

対話入力を伴うコマンド (recommend / create) は、フラグで全入力を与えると
非対話で実行できる (スクリプト / テスト用)。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.authoring import (
    AuthoringError,
    build_attribute,
    save_attribute,
    user_attributes_root,
)
from hersona.core.compatibility import load_matrix
from hersona.core.recommend import DEFAULT_QUIZ, recommend
from hersona.core.weight import WeightLevel, suggest_weight

_WEIGHT_CHOICES = [w.value for w in WeightLevel]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return handler(args)
    except (AuthoringError, KeyError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hersona", description="hersona 属性テンプレート CLI")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="利用可能な属性を一覧")
    p_list.set_defaults(_handler=_cmd_list)

    p_show = sub.add_parser("show", help="属性の詳細")
    p_show.add_argument("name", help="属性名 (例: tsundere) または <category>/<name>")
    p_show.set_defaults(_handler=_cmd_show)

    p_matrix = sub.add_parser("matrix", help="相性マトリクスをダンプ")
    p_matrix.add_argument("--json", action="store_true", help="機械可読 JSON で出力")
    p_matrix.set_defaults(_handler=_cmd_matrix)

    p_blend = sub.add_parser("blend", help="属性をブレンドして注入ブロックを表示")
    p_blend.add_argument("names", nargs="+", help="属性名 (複数可)")
    p_blend.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help="強度 (既定 moderate)"
    )
    p_blend.set_defaults(_handler=_cmd_blend)

    p_rec = sub.add_parser("recommend", help="診断クイズ → 推薦")
    p_rec.add_argument(
        "--answers",
        help="非対話用: 'distance=1,role=1' 形式で回答を指定",
    )
    p_rec.add_argument("--apply", action="store_true", help="推薦ブレンドの注入ブロックも表示")
    p_rec.add_argument(
        "--weight",
        choices=_WEIGHT_CHOICES,
        help="--apply 時の強度 (既定: 適合度スコアから自動推定)",
    )
    p_rec.add_argument("--json", action="store_true", help="機械可読 JSON で出力")
    p_rec.set_defaults(_handler=_cmd_recommend)

    p_create = sub.add_parser("create", help="属性を作成して保存")
    p_create.add_argument("--category", choices=["personality", "speech", "archetype"])
    p_create.add_argument("--name")
    p_create.add_argument("--display-ja")
    p_create.add_argument("--display-en")
    p_create.add_argument(
        "--weight", choices=["none", "mild", "moderate", "strong"], default="moderate"
    )
    p_create.add_argument("--desc-ja")
    p_create.add_argument("--desc-en")
    p_create.add_argument("--example", action="append", dest="examples", help="繰り返し指定可")
    p_create.add_argument("--overwrite", action="store_true")
    p_create.set_defaults(_handler=_cmd_create)

    return parser


def _normalize_name(name: str) -> str:
    """'<category>/<name>' 形式なら name 部分を返す。"""
    return name.split("/", 1)[1] if "/" in name else name


def _cmd_list(args: argparse.Namespace) -> int:
    attrs = available_attributes()
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for name, meta in sorted(attrs.items()):
        by_cat.setdefault(meta["category"], []).append((name, meta["source"]))
    print(f"利用可能な属性 ({len(attrs)} 件):")
    for cat in ("personality", "speech", "archetype"):
        items = by_cat.get(cat, [])
        if not items:
            continue
        print(f"\n{cat}/ ({len(items)})")
        for name, source in items:
            tag = " [user]" if source == "user" else ""
            print(f"  - {name}{tag}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    data = load_attribute(_normalize_name(args.name))
    print(f"=== {data['attribute_category']}/{data['attribute_name']} ===")
    for key in ("display_name_ja", "display_name_en", "weight_dimension", "typical_value_range"):
        if data.get(key):
            print(f"{key}: {data[key]}")
    for key in ("core_traits", "catchphrases", "sentence_endings"):
        if data.get(key):
            print(f"{key}: {len(data[key])} 件 ({', '.join(data[key][:3])} ...)")
    for key in ("second_person", "tone"):
        if data.get(key):
            print(f"{key}: {data[key]}")
    if data.get("compatible_archetypes"):
        print(f"compatible_archetypes: {data['compatible_archetypes']}")
    if data.get("conflicts_with"):
        print(f"conflicts_with: {data['conflicts_with']}")
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    matrix = load_matrix()
    if args.json:
        print(json.dumps(matrix.to_dict(), ensure_ascii=False, indent=2))
        return 0
    for name in matrix.names():
        conf = sorted(matrix.conflicts_of(name))
        comp = sorted(matrix.compatible_of(name))
        print(f"{name}: conflicts={conf} compatible={comp}")
    return 0


def _cmd_blend(args: argparse.Namespace) -> int:
    names = [_normalize_name(n) for n in args.names]
    result = render_blend(names, weight=args.weight)
    if result.conflicts:
        print(f"⚠ conflict: {result.conflicts}", file=sys.stderr)
    print(result.prompt)
    return 0


def _parse_answers(raw: str) -> dict[str, int]:
    answers: dict[str, int] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        qid, _, idx = token.partition("=")
        answers[qid.strip()] = int(idx)
    return answers


def _cmd_recommend(args: argparse.Namespace) -> int:
    if args.answers:
        answers = _parse_answers(args.answers)
    else:
        answers = _interactive_quiz()

    rec = recommend(answers)
    if args.json:
        print(
            json.dumps(
                {"blend": rec.blend, "scores": rec.scores, "dropped": rec.dropped},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print("=== 推薦結果 ===")
    print(f"ブレンド: {' + '.join(rec.blend) if rec.blend else '(該当なし)'}")
    top = rec.ranked()[:5]
    if top:
        print("適合度トップ: " + ", ".join(f"{n}({s:g})" for n, s in top))
    for name, reason in rec.dropped:
        print(f"  落選: {name} — {reason}")

    if args.apply and rec.blend:
        top_score = rec.ranked()[0][1] if rec.ranked() else 0.0
        weight = args.weight or suggest_weight(top_score)
        print(f"\n--- 注入ブロック (強度: {weight}) ---")
        print(render_blend(rec.blend, weight=weight).prompt)
    return 0


def _interactive_quiz() -> dict[str, int]:
    answers: dict[str, int] = {}
    for q in DEFAULT_QUIZ:
        print(f"\n{q.prompt}")
        for i, opt in enumerate(q.options):
            print(f"  [{i}] {opt.label}")
        while True:
            raw = input("選択 (番号): ").strip()
            try:
                idx = int(raw)
                if 0 <= idx < len(q.options):
                    answers[q.id] = idx
                    break
            except ValueError:
                pass
            print("  ※ 有効な番号を入力してください")
    return answers


def _cmd_create(args: argparse.Namespace) -> int:
    if args.name and args.category:
        data = _create_from_flags(args)
    else:
        data = _interactive_create()
    dest = save_attribute(data, overwrite=args.overwrite)
    print(f"保存しました: {dest}")
    print(f"(ユーザー名前空間: {user_attributes_root()})")
    return 0


def _create_from_flags(args: argparse.Namespace) -> dict:
    missing = [
        flag
        for flag, val in {
            "--display-ja": args.display_ja,
            "--display-en": args.display_en,
            "--desc-ja": args.desc_ja,
            "--desc-en": args.desc_en,
            "--example": args.examples,
        }.items()
        if not val
    ]
    if missing:
        raise ValueError(f"必須フラグが不足: {', '.join(missing)}")
    return build_attribute(
        attribute_category=args.category,
        attribute_name=args.name,
        display_name_ja=args.display_ja,
        display_name_en=args.display_en,
        weight_dimension=args.weight,
        description_ja=args.desc_ja,
        description_en=args.desc_en,
        examples=args.examples,
    )


def _interactive_create() -> dict:
    print("=== 属性作成ウィザード ===")
    category = _prompt_choice("カテゴリ", ["personality", "speech", "archetype"])
    name = input("attribute_name (snake_case): ").strip()
    display_ja = input("表示名 (日本語): ").strip()
    display_en = input("表示名 (英語): ").strip()
    weight = _prompt_choice("weight_dimension", ["none", "mild", "moderate", "strong"])
    desc_ja = input("説明 (日本語): ").strip()
    desc_en = input("説明 (英語): ").strip()
    print("examples を 1 行ずつ入力 (空行で終了):")
    examples: list[str] = []
    while True:
        line = input("  example: ").strip()
        if not line:
            break
        examples.append(line)
    return build_attribute(
        attribute_category=category,
        attribute_name=name,
        display_name_ja=display_ja,
        display_name_en=display_en,
        weight_dimension=weight,
        description_ja=desc_ja,
        description_en=desc_en,
        examples=examples or ["(example)"],
    )


def _prompt_choice(label: str, choices: list[str]) -> str:
    while True:
        raw = input(f"{label} {choices}: ").strip()
        if raw in choices:
            return raw
        print(f"  ※ {choices} から選んでください")


if __name__ == "__main__":
    sys.exit(main())
