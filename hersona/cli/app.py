"""hersona CLI 本体 (argparse)。

サブコマンド:
    hersona list                       利用可能な属性を一覧
    hersona show <name>                属性の詳細
    hersona matrix [--json]            相性マトリクスをダンプ
    hersona blend <name> [<name>...]   属性をブレンドしてプロンプト注入ブロックを表示
    hersona recommend [--answers ...]  診断クイズ → 推薦 (→ --apply で注入ブロック)
    hersona create [...]               属性を作成しユーザー名前空間に保存
    hersona measure <name>...          出力テキストの強度指標を採点 (speech 属性必須)

対話入力を伴うコマンド (recommend / create) は、フラグで全入力を与えると
非対話で実行できる (スクリプト / テスト用)。

UI 文言は ``hersona/locales/<lang>.yaml`` のカタログに外部化し、``i18n.tr`` で
参照する。表示言語は ``--lang`` / ``HERSONA_LANG`` / 既定 en で決まる。
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
from hersona.core.constants import CATEGORY_ORDER
from hersona.core.i18n import SUPPORTED_LANGS, resolve_meta, set_active_lang, tr
from hersona.core.intensity import content_language, format_report
from hersona.core.intensity import skip_reason as intensity_skip_reason
from hersona.core.intensity import verify as verify_intensity
from hersona.core.recommend import quiz_for_lang, recommend
from hersona.core.weight import WeightLevel

_WEIGHT_CHOICES = [w.value for w in WeightLevel]


def main(argv: list[str] | None = None) -> int:
    # 表示言語を最初に確定する (設計書 §3.1): --lang > HERSONA_LANG > 既定 en。
    # argparse の help/description もローカライズするため、パーサ構築前に決める。
    raw = sys.argv[1:] if argv is None else argv
    lang = set_active_lang(_peek_lang(raw))
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.lang = lang
    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return handler(args)
    except (AuthoringError, KeyError, ValueError) as e:
        print(f"{tr('error.prefix')}{e}", file=sys.stderr)
        return 1


def _peek_lang(argv: list[str]) -> str | None:
    """パーサ構築前に ``--lang`` の値を先読みする。

    ``--lang ja`` / ``--lang=ja`` の双方に対応。未指定なら None (env/既定へ委譲)。
    """
    for i, token in enumerate(argv):
        if token == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if token.startswith("--lang="):
            return token.split("=", 1)[1]
    return None


def _lang_parser() -> argparse.ArgumentParser:
    """全サブコマンドで共有する ``--lang`` 親パーサ。

    ``hersona --lang ja list`` (前置) と ``hersona list --lang ja`` (後置) の
    両方を受理できるよう、トップレベルと各サブパーサの双方に付与する。
    """
    p = argparse.ArgumentParser(add_help=False)
    # default=SUPPRESS: 親 (top-level) と子 (subparser) の双方に同じ --lang を
    # 持たせると、子の既定値 None が前置指定 (`hersona --lang ja list`) で
    # 解決済みの値を上書きしてしまう。SUPPRESS で「明示時のみ namespace に載る」
    # 挙動にし、どちらの位置で指定しても他方を潰さないようにする。
    p.add_argument(
        "--lang",
        choices=list(SUPPORTED_LANGS),
        default=argparse.SUPPRESS,
        help=tr("cli.lang_help"),
    )
    return p


def _build_parser() -> argparse.ArgumentParser:
    lang_opt = _lang_parser()
    parser = argparse.ArgumentParser(
        prog="hersona", description=tr("cli.description"), parents=[lang_opt]
    )
    sub = parser.add_subparsers(dest="command")

    def add(name: str, **kw: object) -> argparse.ArgumentParser:
        # 全サブコマンドに --lang を継承させる薄いラッパ。
        return sub.add_parser(name, parents=[lang_opt], **kw)

    p_list = add("list", help=tr("help.list"))
    p_list.set_defaults(_handler=_cmd_list)

    p_show = add("show", help=tr("help.show"))
    p_show.add_argument("name", help=tr("help.show_name"))
    p_show.set_defaults(_handler=_cmd_show)

    p_matrix = add("matrix", help=tr("help.matrix"))
    p_matrix.add_argument("--json", action="store_true", help=tr("help.json"))
    p_matrix.set_defaults(_handler=_cmd_matrix)

    p_blend = add("blend", help=tr("help.blend"))
    p_blend.add_argument("names", nargs="+", help=tr("help.names"))
    p_blend.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_blend.set_defaults(_handler=_cmd_blend)

    p_rec = add("recommend", help=tr("help.recommend"))
    p_rec.add_argument("--answers", help=tr("help.rec_answers"))
    p_rec.add_argument("--apply", action="store_true", help=tr("help.rec_apply"))
    p_rec.add_argument("--weight", choices=_WEIGHT_CHOICES, help=tr("help.rec_weight"))
    p_rec.add_argument("--explain", action="store_true", help=tr("help.rec_explain"))
    p_rec.add_argument("--json", action="store_true", help=tr("help.json"))
    p_rec.set_defaults(_handler=_cmd_recommend)

    p_create = add("create", help=tr("help.create"))
    p_create.add_argument("--category", choices=list(CATEGORY_ORDER))
    p_create.add_argument("--name")
    p_create.add_argument("--display-ja")
    p_create.add_argument("--display-en")
    p_create.add_argument(
        "--weight", choices=["none", "mild", "moderate", "strong"], default="moderate"
    )
    p_create.add_argument("--desc-ja")
    p_create.add_argument("--desc-en")
    p_create.add_argument("--example", action="append", dest="examples", help=tr("help.create_example"))
    p_create.add_argument("--overwrite", action="store_true")
    p_create.set_defaults(_handler=_cmd_create)

    p_measure = add("measure", help=tr("help.measure"))
    p_measure.add_argument("names", nargs="+", help=tr("help.names"))
    p_measure.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_measure")
    )
    p_measure.add_argument("--input", help=tr("help.measure_input"))
    p_measure.add_argument("--text", help=tr("help.measure_text"))
    p_measure.set_defaults(_handler=_cmd_measure)

    return parser


def _normalize_name(name: str) -> str:
    """'<category>/<name>' 形式なら name 部分を返す。"""
    return name.split("/", 1)[1] if "/" in name else name


def _cmd_list(args: argparse.Namespace) -> int:
    attrs = available_attributes()
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for name, meta in sorted(attrs.items()):
        by_cat.setdefault(meta["category"], []).append((name, meta["source"]))
    print(tr("list.header", count=len(attrs)))
    for cat in CATEGORY_ORDER:
        items = by_cat.get(cat, [])
        if not items:
            continue
        print("\n" + tr("list.category", category=cat, count=len(items)))
        for name, source in items:
            tag = tr("list.user_tag") if source == "user" else ""
            print(f"  - {name}{tag}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    data = load_attribute(_normalize_name(args.name))
    print(f"=== {data['attribute_category']}/{data['attribute_name']} ===")
    display_name = resolve_meta(data, "display_name")
    if display_name:
        print(f"display_name: {display_name}")
    description = resolve_meta(data, "description")
    if description:
        print(f"description: {description}")
    for key in ("weight_dimension", "typical_value_range"):
        if data.get(key):
            print(f"{key}: {data[key]}")
    for key in ("core_traits", "catchphrases", "sentence_endings"):
        if data.get(key):
            print(f"{key}: {len(data[key])} ({', '.join(data[key][:3])} ...)")
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
        print(tr("blend.conflict", conflicts=result.conflicts), file=sys.stderr)
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
    # 表示言語に応じた既定クイズ (W2: en は英語 speech へ導線するロケール別クイズ)
    quiz = quiz_for_lang()
    if args.answers:
        answers = _parse_answers(args.answers)
    else:
        answers = _interactive_quiz(quiz)

    rec = recommend(answers, quiz=quiz)
    if args.json:
        print(
            json.dumps(
                {
                    "blend": rec.blend,
                    "scores": rec.scores,
                    "dropped": rec.dropped,
                    "rationale": rec.rationale,
                    "alternatives": [
                        {"dropped": d, "alternative": a, "score": s}
                        for d, a, s in rec.alternatives
                    ],
                    "weight_suggestion": rec.weight_suggestion.value,
                    "summary": rec.summary(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(tr("recommend.header"))
    blend = " + ".join(rec.blend) if rec.blend else tr("common.none")
    print(tr("recommend.blend", blend=blend))
    print(tr("recommend.summary", summary=rec.summary()))
    print(tr("recommend.weight", weight=rec.weight_suggestion.value))
    top = rec.ranked()[:5]
    if top:
        items = ", ".join(f"{n}({s:g})" for n, s in top)
        print(tr("recommend.top", items=items))
    for name, reason in rec.dropped:
        print(tr("recommend.dropped", name=name, reason=reason))

    if args.explain:
        print("\n" + tr("recommend.rationale_header"))
        for name in rec.blend:
            reasons = rec.rationale.get(name, [])
            print(f"  {name}:")
            for r in reasons:
                print(f"    - {r}")
        if rec.alternatives:
            print("\n" + tr("recommend.alt_header"))
            for dropped, alt, score in rec.alternatives:
                print(tr("recommend.alt_item", dropped=dropped, alt=alt, score=f"{score:g}"))

    if args.apply and rec.blend:
        weight = args.weight or rec.weight_suggestion.value
        print("\n" + tr("recommend.inject_header", weight=weight))
        print(render_blend(rec.blend, weight=weight).prompt)
    return 0


def _interactive_quiz(quiz) -> dict[str, int]:
    answers: dict[str, int] = {}
    for q in quiz:
        print(f"\n{q.localized_prompt()}")
        for i, opt in enumerate(q.options):
            print(f"  [{i}] {opt.localized_label()}")
        while True:
            raw = input(tr("quiz.prompt_select")).strip()
            try:
                idx = int(raw)
                if 0 <= idx < len(q.options):
                    answers[q.id] = idx
                    break
            except ValueError:
                pass
            print(tr("quiz.invalid_number"))
    return answers


def _cmd_create(args: argparse.Namespace) -> int:
    if args.name and args.category:
        data = _create_from_flags(args)
    else:
        data = _interactive_create()
    dest = save_attribute(data, overwrite=args.overwrite)
    print(tr("create.saved", dest=dest))
    print(tr("create.namespace", root=user_attributes_root()))
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
        raise ValueError(tr("create.missing_flags", flags=", ".join(missing)))
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
    print(tr("create.wizard_header"))
    category = _prompt_choice(tr("create.label_category"), list(CATEGORY_ORDER))
    name = input(tr("create.ask_name")).strip()
    display_ja = input(tr("create.ask_display_ja")).strip()
    display_en = input(tr("create.ask_display_en")).strip()
    weight = _prompt_choice("weight_dimension", ["none", "mild", "moderate", "strong"])
    desc_ja = input(tr("create.ask_desc_ja")).strip()
    desc_en = input(tr("create.ask_desc_en")).strip()
    print(tr("create.ask_examples"))
    examples: list[str] = []
    while True:
        line = input(tr("create.ask_example")).strip()
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
        raw = input(tr("prompt.choice", label=label, choices=choices)).strip()
        if raw in choices:
            return raw
        print(tr("prompt.invalid_choice", choices=choices))


def _cmd_measure(args: argparse.Namespace) -> int:
    if not args.input and args.text is None:
        raise ValueError(tr("measure.need_input"))

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text or ""

    names = [_normalize_name(n) for n in args.names]
    attrs = [load_attribute(n) for n in names]

    reason = intensity_skip_reason(text, attrs)
    if reason == "no_speech":
        print(tr("measure.no_speech"))
        return 0
    if reason == "unsupported_lang":
        print(tr("measure.unsupported_lang", lang=content_language(attrs)))
        return 0
    if reason == "lang_mismatch":
        print(tr("measure.lang_mismatch"))
        return 0

    report = verify_intensity(text, attrs, args.weight)
    if report is None:
        print(tr("measure.no_speech"))
        return 0

    print(format_report(report, args.weight))
    if report.status == "under":
        lo, hi = report.band
        print(
            tr("measure.under", lo=lo, hi=hi, actual=f"{report.score:.0f}"),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
