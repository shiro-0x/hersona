"""hersona CLI 本体 (argparse)。

サブコマンド:
    hersona list                       利用可能な属性を一覧
    hersona show <name>                属性の詳細
    hersona matrix [--json]            相性マトリクスをダンプ
    hersona blend <name> [<name>...]   属性をブレンドしてプロンプト注入ブロックを表示
    hersona diff <name> <name>         2 属性の差分 (共通 / 片側のみ + 相性) を比較
    hersona preview <name> [<name>...] 注入ブロック + サンプルフレーズを即確認
    hersona recommend [--answers ...]  診断クイズ → 推薦 (→ --apply で注入ブロック)
    hersona create [...]               属性を作成しユーザー名前空間に保存
    hersona measure <name>...          出力テキストの強度指標を採点 (speech 属性必須)
    hersona lint-intro [--text|--input]  公開向け自己紹介文の決定論 lint
    hersona save <preset> <name>...    ブレンドを名前付きプリセットとして保存
    hersona presets                    保存済みプリセットを一覧
    hersona load <preset>              保存済みプリセットを注入ブロックとして再生
    hersona export <name>...           ブレンドを他フレームワーク向けにエクスポート
    hersona update [--ref <ref>]       公開属性データを GitHub から最新化 (再インストール不要)

対話入力を伴うコマンド (recommend / create) は、フラグで全入力を与えると
非対話で実行できる (スクリプト / テスト用)。

UI 文言は ``hersona/locales/<lang>.yaml`` のカタログに外部化し、``i18n.tr`` で
参照する。表示言語は ``--lang`` / ``HERSONA_LANG`` / 既定 en で決まる。

シェル補完: ``argcomplete`` が入っていれば属性名・プリセット名のタブ補完が効く
(``pip install "hersona[completion]"`` → ``eval "$(register-python-argcomplete hersona)"``)。
未インストールでも CLI は通常どおり動作する (補完だけが無効)。
"""
# PYTHON_ARGCOMPLETE_OK
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.authoring import (
    AuthoringError,
    build_attribute,
    save_attribute,
    user_attributes_root,
)
from hersona.core.compatibility import ConflictFix, load_matrix
from hersona.core.constants import CATEGORY_ORDER
from hersona.core.diff import diff_attributes
from hersona.core.export import EXPORT_FORMATS, export_blend
from hersona.core.i18n import SUPPORTED_LANGS, resolve_meta, set_active_lang, tr
from hersona.core.intensity import (
    content_language,
    format_report,
    pre_response_check_prompt,
)
from hersona.core.intensity import skip_reason as intensity_skip_reason
from hersona.core.intensity import verify as verify_intensity
from hersona.core.persistent import run_persistent
from hersona.core.presets import (
    PresetError,
    list_presets,
    load_preset,
    save_preset,
)
from hersona.core.recommend import quiz_for_lang, recommend
from hersona.core.sample_dialogue import generate_samples
from hersona.core.self_intro import (
    lint_memory_self_intro_canonical,
    lint_self_intro,
    merge_self_intro_guide,
)
from hersona.core.soul import default_soul_path, detect_lang_from_names, resolve_memory, write_soul
from hersona.core.targets import (
    TARGET_ALIASES,
    available_targets,
    write_target,
)
from hersona.core.use_cases import (
    UseCaseError,
    available_use_cases,
    load_use_case,
    render_use_case_block,
    validate_use_case,
)
from hersona.core.weight import WeightLevel

from . import render

_WEIGHT_CHOICES = [w.value for w in WeightLevel]


def main(argv: list[str] | None = None) -> int:
    # 表示言語を最初に確定する (設計書 §3.1): --lang > HERSONA_LANG > 既定 en。
    # argparse の help/description もローカライズするため、パーサ構築前に決める。
    raw = sys.argv[1:] if argv is None else argv
    lang = set_active_lang(_peek_lang(raw))
    parser = _build_parser()
    _try_argcomplete(parser)
    args = parser.parse_args(argv)
    args.lang = lang
    render.set_plain(getattr(args, "plain", False))
    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return handler(args)
    except (AuthoringError, PresetError, KeyError, ValueError) as e:
        print(f"{tr('error.prefix')}{e}", file=sys.stderr)
        return 1


def _try_argcomplete(parser: argparse.ArgumentParser) -> None:
    """``argcomplete`` が入っていればシェル補完フックを呼ぶ (任意依存)。

    補完中 (``_ARGCOMPLETE`` 環境変数あり) は argcomplete が出力して exit する。
    通常実行では何もしない。未インストールなら静かに no-op (補完だけ無効)。
    """
    try:
        import argcomplete
    except ImportError:
        return
    argcomplete.autocomplete(parser)


def _attribute_completer(prefix: str, **_kwargs: object) -> list[str]:
    """属性名 (public + user) のタブ補完候補を返す (argcomplete 用)。"""
    try:
        names = available_attributes()
    except Exception:
        return []
    return sorted(n for n in names if n.startswith(prefix))


def _preset_completer(prefix: str, **_kwargs: object) -> list[str]:
    """保存済みプリセット名のタブ補完候補を返す (argcomplete 用)。"""
    try:
        names = [p.name for p in list_presets()]
    except Exception:
        return []
    return sorted(n for n in names if n.startswith(prefix))


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
    # --plain: rich を入れていても色付きテーブル/パネルを無効化する。
    # SUPPRESS の理由は --lang と同じ (前置/後置どちらでも潰し合わない)。
    p.add_argument(
        "--plain",
        action="store_true",
        default=argparse.SUPPRESS,
        help=tr("cli.plain_help"),
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
    p_show.add_argument("name", help=tr("help.show_name")).completer = _attribute_completer
    p_show.set_defaults(_handler=_cmd_show)

    p_use_case = add("use-case", help="List or show Operating Mode / use-case prompt packs")
    use_case_sub = p_use_case.add_subparsers(dest="use_case_command")
    p_use_case_list = use_case_sub.add_parser("list", parents=[lang_opt], help="List use cases")
    p_use_case_list.add_argument("--category", help="Filter by category (e.g. technical)")
    p_use_case_list.add_argument("--tag", help="Filter by tag (e.g. coding)")
    p_use_case_list.set_defaults(_handler=_cmd_use_case_list)
    p_use_case_show = use_case_sub.add_parser("show", parents=[lang_opt], help="Show a use case")
    p_use_case_show.add_argument("name", help="Use-case ID")
    p_use_case_show.set_defaults(_handler=_cmd_use_case_show)
    p_use_case_validate = use_case_sub.add_parser(
        "validate", parents=[lang_opt], help="Validate a use-case YAML file"
    )
    p_use_case_validate.add_argument("file", help="Path to a use-case YAML file")
    p_use_case_validate.set_defaults(_handler=_cmd_use_case_validate)

    p_matrix = add("matrix", help=tr("help.matrix"))
    p_matrix.add_argument("--json", action="store_true", help=tr("help.json"))
    p_matrix.set_defaults(_handler=_cmd_matrix)

    p_blend = add("blend", help=tr("help.blend"))
    p_blend.add_argument("names", nargs="+", help=tr("help.names")).completer = _attribute_completer
    p_blend.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_blend.add_argument("--use-case", dest="use_case", help="Operating Mode / use-case prompt pack ID")
    p_blend.add_argument("--suggest", action="store_true", help=tr("help.suggest"))
    p_blend.set_defaults(_handler=_cmd_blend)

    p_diff = add("diff", help=tr("help.diff"))
    p_diff.add_argument("name_a", help=tr("help.diff_name")).completer = _attribute_completer
    p_diff.add_argument("name_b", help=tr("help.diff_name")).completer = _attribute_completer
    p_diff.set_defaults(_handler=_cmd_diff)

    p_preview = add("preview", help=tr("help.preview"))
    p_preview.add_argument("names", nargs="+", help=tr("help.names")).completer = _attribute_completer
    p_preview.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_preview.add_argument(
        "--count", type=int, default=3, help=tr("help.preview_count")
    )
    p_preview.add_argument("--suggest", action="store_true", help=tr("help.suggest"))
    p_preview.set_defaults(_handler=_cmd_preview)

    p_rec = add("recommend", help=tr("help.recommend"))
    p_rec.add_argument("--answers", help=tr("help.rec_answers"))
    p_rec.add_argument(
        "--quiz-mode",
        choices=["v1", "v2"],
        default="v1",
        help=tr("help.rec_quiz_mode"),
    )
    p_rec.add_argument("--apply", action="store_true", help=tr("help.rec_apply"))
    p_rec.add_argument("--weight", choices=_WEIGHT_CHOICES, help=tr("help.rec_weight"))
    p_rec.add_argument("--explain", action="store_true", help=tr("help.rec_explain"))
    p_rec.add_argument("--top", type=int, default=1, help=tr("help.rec_top"))
    p_rec.add_argument(
        "--generate-samples",
        action="store_true",
        help=tr("help.rec_generate_samples"),
    )
    p_rec.add_argument(
        "--sample-count",
        type=int,
        default=3,
        help=tr("help.rec_sample_count"),
    )
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
    p_measure.add_argument("names", nargs="+", help=tr("help.names")).completer = _attribute_completer
    p_measure.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_measure")
    )
    p_measure.add_argument("--input", help=tr("help.measure_input"))
    p_measure.add_argument("--text", help=tr("help.measure_text"))
    p_measure.add_argument("--strict", action="store_true", help=tr("help.measure_strict"))
    p_measure.add_argument(
        "--check-prompt", action="store_true", help=tr("help.measure_check_prompt")
    )
    p_measure.set_defaults(_handler=_cmd_measure)

    p_lint_intro = add("lint-intro", help=tr("help.lint_intro"))
    p_lint_intro.add_argument("--input", help=tr("help.lint_intro_input"))
    p_lint_intro.add_argument("--text", help=tr("help.lint_intro_text"))
    p_lint_intro.add_argument(
        "--allow-handle",
        action="append",
        default=[],
        help=tr("help.lint_intro_allow_handle"),
    )
    p_lint_intro.add_argument(
        "--canonical", action="store_true", help=tr("help.lint_intro_canonical")
    )
    p_lint_intro.add_argument("--json", action="store_true", help=tr("help.lint_intro_json"))
    p_lint_intro.set_defaults(_handler=_cmd_lint_intro)

    p_save = add("save", help=tr("help.save"))
    p_save.add_argument("preset_name", help=tr("help.save_name"))
    p_save.add_argument("names", nargs="+", help=tr("help.names")).completer = _attribute_completer
    p_save.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_save.add_argument("--note", default="", help=tr("help.save_note"))
    p_save.add_argument("--overwrite", action="store_true", help=tr("help.save_overwrite"))
    p_save.set_defaults(_handler=_cmd_save)

    p_presets = add("presets", help=tr("help.presets"))
    p_presets.set_defaults(_handler=_cmd_presets)

    p_load = add("load", help=tr("help.load"))
    p_load.add_argument("preset_name", help=tr("help.load_name")).completer = _preset_completer
    p_load.add_argument("--weight", choices=_WEIGHT_CHOICES, help=tr("help.load_weight"))
    p_load.set_defaults(_handler=_cmd_load)

    p_export = add("export", help=tr("help.export"))
    p_export.add_argument("names", nargs="+", help=tr("help.names")).completer = _attribute_completer
    p_export.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_export.add_argument(
        "--format", choices=list(EXPORT_FORMATS), default="json", help=tr("help.export_format")
    )
    p_export.add_argument("--use-case", dest="use_case", help="Operating Mode / use-case prompt pack ID")
    p_export.set_defaults(_handler=_cmd_export)

    # ROADMAP §⑤: SOUL.md 永続化
    p_soul = add("soul", help=tr("help.soul"))
    p_soul.add_argument(
        "names", nargs="+", help=tr("help.names")
    ).completer = _attribute_completer
    p_soul.add_argument(
        "--profile", default="default", help=tr("help.soul_profile")
    )
    p_soul.add_argument(
        "--output", default=None, help=tr("help.soul_output")
    )
    p_soul.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_soul.add_argument(
        "--name", default="Libra", help=tr("help.soul_name")
    )
    p_soul.add_argument(
        "--append", action="store_true", help=tr("help.soul_append")
    )
    p_soul.add_argument(
        "--overwrite", action="store_true", help=tr("help.soul_overwrite")
    )
    p_soul.add_argument(
        "--force", action="store_true", help=tr("help.soul_force")
    )
    p_soul.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help=tr("help.soul_dry_run")
    )
    p_soul.add_argument("--memory", default=None, help=tr("help.soul_memory"))
    p_soul.add_argument("--memory-file", default=None, help=tr("help.soul_memory_file"))
    _register_self_intro_memory_flags(p_soul)
    p_soul.add_argument("--use-case", dest="use_case", help="Operating Mode / use-case prompt pack ID")
    p_soul.set_defaults(_handler=_cmd_soul)

    # ROADMAP §⑤.1: persistent モード (SOUL.md 自動書き出し)
    p_persistent = add("persistent", help=tr("help.persistent"))
    p_persistent.add_argument(
        "names", nargs="+", help=tr("help.names")
    ).completer = _attribute_completer
    p_persistent.add_argument(
        "--weight", choices=_WEIGHT_CHOICES, default="moderate", help=tr("help.weight_blend")
    )
    p_persistent.add_argument(
        "--profile", default="default", help=tr("help.soul_profile")
    )
    p_persistent.add_argument(
        "--force", action="store_true", help=tr("help.persistent_force")
    )
    p_persistent.add_argument(
        "--without-soul", action="store_true", help=tr("help.persistent_without_soul")
    )
    p_persistent.add_argument(
        "--without-config", action="store_true", help=tr("help.persistent_without_config")
    )
    p_persistent.add_argument(
        "--config-yaml-output", default=None, help=tr("help.persistent_yaml_output")
    )
    p_persistent.add_argument(
        "--auto-config",
        action="store_true",
        dest="auto_config",
        help=tr("help.persistent_auto_config"),
    )
    p_persistent.add_argument(
        "--config-path",
        default=None,
        dest="config_path",
        help=tr("help.persistent_config_path"),
    )
    p_persistent.add_argument(
        "--apply",
        action="store_true",
        dest="apply",
        help=tr("help.persistent_apply"),
    )
    p_persistent.add_argument(
        "--target",
        choices=["hermes", *available_targets(), *TARGET_ALIASES],
        default="hermes",
        help=tr("help.persistent_target"),
    )
    p_persistent.add_argument(
        "--global",
        action="store_true",
        dest="global_target",
        help=tr("help.persistent_global"),
    )
    p_persistent.add_argument(
        "--output",
        default=None,
        dest="target_output",
        help=tr("help.persistent_output"),
    )
    p_persistent.add_argument("--memory", default=None, help=tr("help.persistent_memory"))
    p_persistent.add_argument(
        "--memory-file", default=None, help=tr("help.persistent_memory_file")
    )
    _register_self_intro_memory_flags(p_persistent)
    p_persistent.add_argument("--use-case", dest="use_case", help="Operating Mode / use-case prompt pack ID")
    p_persistent.set_defaults(_handler=_cmd_persistent)

    # 公開属性データを GitHub から最新化する (再インストール不要)。
    p_update = add("update", help=tr("help.update"))
    p_update.add_argument("--ref", default="main", help=tr("help.update_ref"))
    p_update.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help=tr("help.update_dry_run")
    )
    p_update.add_argument("--clear", action="store_true", help=tr("help.update_clear"))
    p_update.set_defaults(_handler=_cmd_update)

    return parser


def _normalize_name(name: str) -> str:
    """'<category>/<name>' 形式なら name 部分を返す。"""
    return name.split("/", 1)[1] if "/" in name else name


def _register_self_intro_memory_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--with-self-intro-guide",
        action="store_true",
        help=tr("help.with_self_intro_guide"),
    )
    parser.add_argument(
        "--lint-self-intro",
        action="store_true",
        help=tr("help.lint_self_intro_on_memory"),
    )
    parser.add_argument(
        "--lint-self-intro-strict",
        action="store_true",
        dest="lint_self_intro_strict",
        help=tr("help.lint_self_intro_strict"),
    )
    parser.add_argument(
        "--allow-handle",
        action="append",
        dest="allow_handles",
        default=[],
        help=tr("help.lint_intro_allow_handle"),
    )


def _apply_self_intro_memory_options(
    memory: dict[str, str] | None,
    args: argparse.Namespace,
    *,
    blend_names: list[str],
) -> tuple[dict[str, str] | None, int | None]:
    """Merge guide defaults and optional lint on self_intro_canonical."""
    if getattr(args, "with_self_intro_guide", False):
        lang = detect_lang_from_names(blend_names)
        memory = merge_self_intro_guide(memory, lang=lang)
        memory = resolve_memory(memory=memory)

    do_lint = getattr(args, "lint_self_intro", False) or getattr(
        args, "lint_self_intro_strict", False
    )
    if do_lint:
        allow = frozenset(getattr(args, "allow_handles", None) or [])
        result = lint_memory_self_intro_canonical(
            memory, allow_handles=allow, canonical=True
        )
        if result is None:
            sys.stderr.write(tr("soul.lint_self_intro_skipped") + "\n")
        elif not result.ok:
            sys.stderr.write(tr("lint_intro.fail", count=len(result.violations)) + "\n")
            for v in result.violations:
                sys.stderr.write(
                    tr("lint_intro.item", rule=v.rule, message=v.message, excerpt=v.excerpt)
                    + "\n"
                )
            if getattr(args, "lint_self_intro_strict", False):
                return memory, 1
    return memory, None


def _resolve_cli_memory(
    memory_json: str | None, memory_file: str | None
) -> tuple[dict[str, str] | None, str | None]:
    """Parse --memory / --memory-file. Returns (memory, error_message)."""
    if memory_json and memory_file:
        return None, tr("error.memory_mutually_exclusive")
    try:
        memory: dict[str, str] | None = None
        if memory_json:
            memory = json.loads(memory_json)
        return resolve_memory(memory=memory, memory_file=memory_file), None
    except json.JSONDecodeError as e:
        return None, f"{tr('error.prefix')}{e}"
    except ValueError as e:
        return None, f"{tr('error.prefix')}{e}"


def _cmd_list(args: argparse.Namespace) -> int:
    attrs = available_attributes()
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for name, meta in sorted(attrs.items()):
        by_cat.setdefault(meta["category"], []).append((name, meta["source"]))
    if render.rich_enabled():
        return _list_rich(by_cat, total=len(attrs))
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


def _list_rich(by_cat: dict[str, list[tuple[str, str]]], *, total: int) -> int:
    from rich.table import Table

    table = Table(title=tr("list.header", count=total), title_justify="left")
    table.add_column(tr("list.col_category"), no_wrap=True)
    table.add_column(tr("list.col_attribute"))
    table.add_column(tr("list.col_source"), no_wrap=True)
    for cat in CATEGORY_ORDER:
        items = by_cat.get(cat, [])
        if not items:
            continue
        style = render.CATEGORY_STYLE.get(cat, "white")
        for i, (name, source) in enumerate(items):
            # カテゴリ名は各グループの先頭行にだけ出して縦の見通しを良くする。
            cat_cell = f"[{style}]{cat}[/{style}]" if i == 0 else ""
            src_cell = "[dim]user[/dim]" if source == "user" else ""
            table.add_row(cat_cell, name, src_cell)
    render.console().print(table)
    return 0


def _show_lines(data: dict) -> list[tuple[str, str]]:
    """show 用の (ラベル, 値) 行を組み立てる (rich / プレーン共通)。"""
    rows: list[tuple[str, str]] = []
    display_name = resolve_meta(data, "display_name")
    if display_name:
        rows.append(("display_name", display_name))
    description = resolve_meta(data, "description")
    if description:
        rows.append(("description", description))
    for key in ("weight_dimension", "typical_value_range"):
        if data.get(key):
            rows.append((key, str(data[key])))
    for key in ("core_traits", "catchphrases", "sentence_endings"):
        if data.get(key):
            def _to_str(item: object) -> str:
                if isinstance(item, dict):
                    return str(item.get("phrase", ""))
                return str(item)
            previews = ", ".join(_to_str(v) for v in data[key][:3])
            rows.append((key, f"{len(data[key])} ({previews} ...)"))
    for key in ("second_person", "tone"):
        if data.get(key):
            rows.append((key, str(data[key])))
    if data.get("compatible_archetypes"):
        rows.append(("compatible_archetypes", str(data["compatible_archetypes"])))
    if data.get("conflicts_with"):
        rows.append(("conflicts_with", str(data["conflicts_with"])))
    return rows


def _cmd_show(args: argparse.Namespace) -> int:
    data = load_attribute(_normalize_name(args.name))
    title = f"{data['attribute_category']}/{data['attribute_name']}"
    rows = _show_lines(data)
    if render.rich_enabled():
        return _show_rich(title, data["attribute_category"], rows)
    print(f"=== {title} ===")
    for label, value in rows:
        print(f"{label}: {value}")
    return 0


def _cmd_use_case_list(args: argparse.Namespace) -> int:
    cases = available_use_cases()
    category = getattr(args, "category", None)
    tag = getattr(args, "tag", None)
    if category:
        cases = {k: v for k, v in cases.items() if v.get("category") == category}
    if tag:
        cases = {k: v for k, v in cases.items() if tag in (v.get("tags") or [])}
    print(f"Available use cases ({len(cases)}):")
    for name, meta in sorted(cases.items()):
        display = resolve_meta(meta, "display_name") or name
        desc = resolve_meta(meta, "description")
        badge = f"[{meta.get('category', '?')}/{meta.get('risk_level', '?')}]"
        user_tag = tr("list.user_tag") if meta.get("source") == "user" else ""
        print(f"  - {name} ({display}) {badge}{user_tag}: {desc}")
    return 0


def _cmd_use_case_show(args: argparse.Namespace) -> int:
    data = load_use_case(args.name)
    print(render_use_case_block(data), end="")
    return 0


def _cmd_use_case_validate(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Invalid YAML: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("Invalid use case: top-level mapping expected", file=sys.stderr)
        return 1
    try:
        validate_use_case(data)
    except UseCaseError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"OK: {data['use_case_id']} ({path})")
    return 0


def _show_rich(title: str, category: str, rows: list[tuple[str, str]]) -> int:
    from rich.panel import Panel
    from rich.table import Table

    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", no_wrap=True, style="bold")
    grid.add_column(overflow="fold")
    for label, value in rows:
        style = "red" if label == "conflicts_with" else "green" if label == "compatible_archetypes" else ""
        grid.add_row(label, f"[{style}]{value}[/{style}]" if style else value)
    border = render.CATEGORY_STYLE.get(category, "white")
    render.console().print(Panel(grid, title=title, border_style=border, title_align="left"))
    return 0


def _relation_label(result) -> str:
    """relation を表示用ラベルに (None なら未収録)。"""
    if result.relation is None:
        return tr("diff.relation_unknown")
    return result.relation.value


def _cmd_diff(args: argparse.Namespace) -> int:
    name_a = _normalize_name(args.name_a)
    name_b = _normalize_name(args.name_b)
    lang = getattr(args, "lang", "en") or "en"
    result = diff_attributes(name_a, name_b, lang=lang)
    if render.rich_enabled():
        return _diff_rich(result)

    print(tr("diff.header", a=name_a, b=name_b))
    print(tr("diff.category", a=result.category_a, b=result.category_b))
    print(tr("diff.relation", relation=_relation_label(result)))
    for s in result.scalars:
        print(f"\n[{s.field}]")
        print(tr("diff.scalar_a", name=name_a, value=s.a or "-"))
        print(tr("diff.scalar_b", name=name_b, value=s.b or "-"))
    for f in result.lists:
        print(f"\n[{f.field}]")
        if f.common:
            print(tr("diff.common", items=", ".join(f.common)))
        if f.only_a:
            print(tr("diff.only", name=name_a, items=", ".join(f.only_a)))
        if f.only_b:
            print(tr("diff.only", name=name_b, items=", ".join(f.only_b)))
    return 0


def _diff_rich(result) -> int:
    from rich.table import Table

    relation = _relation_label(result)
    rel_style = {"conflict": "bold red", "compatible": "bold green"}.get(relation, "dim")
    title = tr("diff.header", a=result.name_a, b=result.name_b)

    table = Table(title=title, title_justify="left", show_lines=False)
    table.add_column(tr("diff.col_field"), no_wrap=True, style="bold")
    table.add_column(result.name_a, overflow="fold")
    table.add_column(result.name_b, overflow="fold")
    table.add_row("category", result.category_a, result.category_b)
    table.add_row("relation", f"[{rel_style}]{relation}[/{rel_style}]", "")
    for s in result.scalars:
        table.add_row(s.field, s.a or "-", s.b or "-")
    for f in result.lists:
        common = ("[green]= " + ", ".join(f.common) + "[/green]\n") if f.common else ""
        table.add_row(
            f.field,
            common + ", ".join(f.only_a),
            common + ", ".join(f.only_b),
        )
    render.console().print(table)
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


def _print_conflict_suggestions(names: list[str]) -> None:
    """conflict 解消の代替案を stderr に出す (--suggest 用)。

    stdout の注入ブロックを汚さないよう、助言はすべて stderr に流す。
    """
    fixes: list[ConflictFix] = load_matrix().suggest_blend_fixes(names)
    if not fixes:
        return
    use_rich = render.rich_enabled()
    ec = render.err_console() if use_rich else None
    header = tr("suggest.header")
    if ec is not None:
        ec.print(header, style="bold")
    else:
        print(header, file=sys.stderr)
    for fix in fixes:
        a, b = fix.conflict
        line = tr(
            "suggest.item",
            drop=fix.drop,
            a=a,
            b=b,
            alts=", ".join(fix.alternatives),
        )
        if ec is not None:
            ec.print(line)
        else:
            print(line, file=sys.stderr)


def _cmd_blend(args: argparse.Namespace) -> int:
    names = [_normalize_name(n) for n in args.names]
    result = render_blend(names, weight=args.weight, use_case=getattr(args, "use_case", None))
    if result.conflicts:
        render.warn(tr("blend.conflict", conflicts=result.conflicts))
        if getattr(args, "suggest", False):
            _print_conflict_suggestions(names)
    print(result.prompt)
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    names = [_normalize_name(n) for n in args.names]
    blend_label = " + ".join(names)
    print(tr("preview.header", blend=blend_label, weight=args.weight))

    result = render_blend(names, weight=args.weight)
    if result.conflicts:
        render.warn(tr("preview.conflict_warn", conflicts=result.conflicts))
        if getattr(args, "suggest", False):
            _print_conflict_suggestions(names)

    print(tr("preview.inject_header"))
    print(result.prompt)

    print(tr("preview.samples_header"))
    lang = getattr(args, "lang", "en") or "en"
    samples = generate_samples(names, count=args.count, lang=lang)
    if samples:
        for s in samples:
            print(f"  • {s}")
    else:
        print(tr("preview.no_samples"))
    return 0


def _parse_answers(raw: str) -> dict[str, int]:
    answers: dict[str, int] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        qid, _, idx = token.partition("=")
        qid = qid.strip()
        idx = idx.strip()
        # v2 決定木形式: "q1=a" / "q1=b" → 0/1 に変換
        if idx in ("a", "b"):
            idx = 0 if idx == "a" else 1
        answers[qid] = int(idx)
    return answers


def _cmd_recommend(args: argparse.Namespace) -> int:
    # クイズモード切替 (v1: 既定の 9 問線形 / v2: 決定木)
    if getattr(args, "quiz_mode", "v1") == "v2":
        from hersona.core.recommend import load_v2_quiz
        quiz = load_v2_quiz()
    else:
        # 表示言語に応じた既定クイズ (W2: en は英語 speech へ導線するロケール別クイズ)
        quiz = quiz_for_lang()
    if args.answers:
        answers = _parse_answers(args.answers)
    else:
        answers = _interactive_quiz(quiz)

    top = getattr(args, "top", 1) or 1
    generate_samples = getattr(args, "generate_samples", False)
    sample_count = getattr(args, "sample_count", 3) or 3
    rec = recommend(
        answers,
        top=top,
        quiz=quiz,
        generate_samples=generate_samples,
        sample_count=sample_count,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "blend": rec.blend,
                    "candidates": rec.candidates,
                    "sample_dialogue": rec.sample_dialogue,
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
        if rec.intensity_baseline is not None:
            lo, hi = rec.intensity_baseline.band
            print(
                tr(
                    "recommend.baseline_recorded",
                    score=f"{rec.intensity_baseline.score:.0f}",
                    lo=lo,
                    hi=hi,
                    weight=weight,
                )
            )
    return 0


def _is_decision_tree_quiz(quiz) -> bool:
    """クイズが v2 決定木 (いずれかの選択肢に next_id) か判定する。

    全選択肢の next_id が None なら v1 線形クイズとみなす (= リスト順に表示)。
    どれか 1 つでも next_id を持てば v2 決定木。
    """
    for q in quiz:
        for opt in q.options:
            if getattr(opt, "next_id", None) is not None:
                return True
    return False


def _interactive_quiz(quiz) -> dict[str, int]:
    """CLI 対話式クイズ。

    v1 線形クイズ (next_id なし) では全質問を順に表示。
    v2 決定木クイズ (next_id あり) ではユーザ回答に応じて次の質問を動的に辿る。
    """
    answers: dict[str, int] = {}
    by_id = {q.id: q for q in quiz}

    if _is_decision_tree_quiz(quiz):
        # v2 決定木: 最初の質問から開始、回答に応じて next_id を辿る
        current_id: str | None = quiz[0].id
    else:
        # v1 線形: リスト順に表示 (Q1, Q2, ..., Q9)
        _interactive_linear_quiz(quiz, answers)
        return answers

    while current_id is not None:
        q = by_id.get(current_id)
        if q is None:
            # バリデータが保証するはずだが、念のため抜ける
            break
        print(f"\n{q.localized_prompt()}")
        for i, opt in enumerate(q.options):
            label = opt.localized_label()
            # 2 択のときは a/b ヒントも表示 (CLI 入力補助)
            hint = ["a", "b"][i] if len(q.options) == 2 else f"[{i}]"
            print(f"  {hint} {label}")
        while True:
            raw = input(tr("quiz.prompt_select")).strip()
            # 2 択: a/b を受け付け、3 択以上: 数値インデックス
            if len(q.options) == 2 and raw in ("a", "b"):
                idx = 0 if raw == "a" else 1
            else:
                try:
                    idx = int(raw)
                except ValueError:
                    print(tr("quiz.invalid_number"))
                    continue
            if 0 <= idx < len(q.options):
                answers[q.id] = idx
                # 次の質問を next_id で決める
                current_id = q.options[idx].next_id
                break
            print(tr("quiz.invalid_number"))
    return answers


def _interactive_linear_quiz(quiz, answers: dict[str, int]) -> None:
    """v1 線形クイズ用ヘルパ (全質問を順に表示)。"""
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
    if not args.input and args.text is None and not args.check_prompt:
        raise ValueError(tr("measure.need_input"))

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text or ""

    names = [_normalize_name(n) for n in args.names]
    attrs = [load_attribute(n) for n in names]

    if args.check_prompt:
        prompt = pre_response_check_prompt(
            names,
            args.weight,
            last_response=text or None,
            lang=getattr(args, "lang", None) or "en",
        )
        print(prompt, end="")
        return 0

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
    if args.strict and report.status in ("under", "over"):
        prompt = pre_response_check_prompt(
            names,
            args.weight,
            last_response=text,
            lang=getattr(args, "lang", None) or "en",
        )
        print(prompt, file=sys.stderr, end="")
    return 0


def _cmd_lint_intro(args: argparse.Namespace) -> int:
    if bool(args.input) == (args.text is not None):
        raise ValueError(tr("lint_intro.need_input"))

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = args.text or ""

    result = lint_self_intro(
        text,
        allow_handles=frozenset(args.allow_handle or []),
        canonical=args.canonical,
    )
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif result.ok:
        print(tr("lint_intro.pass"))
    else:
        print(tr("lint_intro.fail", count=len(result.violations)))
        for v in result.violations:
            print(tr("lint_intro.item", rule=v.rule, message=v.message, excerpt=v.excerpt))
    return 0 if result.ok else 1


def _cmd_save(args: argparse.Namespace) -> int:
    names = [_normalize_name(n) for n in args.names]
    # 属性の実在を確認し、未知の属性は KeyError → exit 1 で弾く。
    for n in names:
        load_attribute(n)
    # conflict があっても保存は妨げない (警告のみ)。
    result = render_blend(names, weight=args.weight)
    if result.conflicts:
        render.warn(tr("save.conflict_warn", conflicts=result.conflicts))
    dest = save_preset(
        args.preset_name,
        names,
        weight=args.weight,
        note=args.note,
        overwrite=args.overwrite,
    )
    print(tr("save.saved", dest=dest))
    print(tr("save.blend", name=args.preset_name, attributes=" + ".join(names), weight=args.weight))
    return 0


def _cmd_presets(args: argparse.Namespace) -> int:
    presets = list_presets()
    if not presets:
        print(tr("presets.none"))
        return 0
    if render.rich_enabled():
        return _presets_rich(presets)
    print(tr("presets.header", count=len(presets)))
    for p in presets:
        note = tr("presets.note_suffix", note=p.note) if p.note else ""
        print(
            tr(
                "presets.item",
                name=p.name,
                attributes=" + ".join(p.attributes),
                weight=p.weight,
                note=note,
            )
        )
    return 0


def _presets_rich(presets) -> int:
    from rich.table import Table

    table = Table(title=tr("presets.header", count=len(presets)), title_justify="left")
    table.add_column(tr("presets.col_name"), no_wrap=True, style="bold")
    table.add_column(tr("presets.col_attributes"))
    table.add_column(tr("presets.col_weight"), no_wrap=True)
    table.add_column(tr("presets.col_note"), overflow="fold")
    for p in presets:
        table.add_row(p.name, " + ".join(p.attributes), p.weight, p.note)
    render.console().print(table)
    return 0


def _cmd_load(args: argparse.Namespace) -> int:
    preset = load_preset(args.preset_name)
    weight = args.weight or preset.weight
    result = render_blend(preset.attributes, weight=weight)
    print(tr("load.header", name=preset.name, weight=weight))
    if result.conflicts:
        render.warn(tr("load.conflict_warn", conflicts=result.conflicts))
    print(result.prompt)
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    names = [_normalize_name(n) for n in args.names]
    print(export_blend(names, weight=args.weight, fmt=args.format, use_case=getattr(args, "use_case", None)))
    return 0


def _cmd_soul(args: argparse.Namespace) -> int:
    """blend を SOUL.md 形式で `~/.hermes/profiles/<name>/SOUL.md` に書き出す。"""
    names = [_normalize_name(n) for n in args.names]
    output = (
        Path(args.output)
        if args.output
        else default_soul_path(args.profile)
    )

    memory, mem_err = _resolve_cli_memory(args.memory, args.memory_file)
    if mem_err:
        sys.stderr.write(mem_err + "\n")
        return 1

    memory, intro_exit = _apply_self_intro_memory_options(memory, args, blend_names=names)
    if intro_exit is not None:
        return intro_exit

    if args.dry_run:
        # ドライラン: ファイルに書かず標準出力にダンプ
        from hersona.core.soul import render_soul
        print(
            render_soul(
                names, weight=args.weight, name=args.name, memory=memory, use_case=args.use_case
            )
        )
        return 0

    # 既存ファイルの確認プロンプト (--overwrite / --force / --append / --yes で分岐)
    if output.exists() and not (args.overwrite or args.force or args.append):
        sys.stderr.write(
            f"SOUL.md が既に存在します: {output}\n"
            "上書きするには --overwrite または --force を指定してください。\n"
            "追記するには --append を指定してください。\n"
        )
        return 1

    try:
        result = write_soul(
            output,
            names,
            weight=args.weight,
            name=args.name,
            append=args.append,
            overwrite=args.overwrite,
            force=args.force,
            memory=memory,
            use_case=args.use_case,
        )
    except (FileExistsError, FileNotFoundError, ValueError) as e:
        sys.stderr.write(f"エラー: {e}\n")
        return 1

    print(
        tr(
            "soul.written",
            path=result.output_path,
            names=", ".join(result.blend_names),
            weight=result.weight.value,
            lang=result.lang,
        )
    )
    return 0


def _cmd_persistent(args: argparse.Namespace) -> int:
    """persistent モード: SOUL.md 自動書き出し + config.yaml ブロック表示。"""
    names = [_normalize_name(n) for n in args.names]

    memory, mem_err = _resolve_cli_memory(args.memory, args.memory_file)
    if mem_err:
        sys.stderr.write(mem_err + "\n")
        return 1

    memory, intro_exit = _apply_self_intro_memory_options(memory, args, blend_names=names)
    if intro_exit is not None:
        return intro_exit

    # Hermes 以外のターゲット (Claude Code / Codex / Cursor / Gemini)
    if args.target != "hermes":
        return _cmd_persistent_target(args, names)

    try:
        result = run_persistent(
            names,
            weight=args.weight,
            profile=args.profile,
            without_soul=args.without_soul,
            without_config=args.without_config,
            force=args.force,
            config_yaml_output=args.config_yaml_output,
            auto_config=args.auto_config,
            config_path=args.config_path,
            apply=args.apply,
            memory=memory,
            use_case=args.use_case,
        )
    except (FileExistsError, FileNotFoundError, ValueError) as e:
        sys.stderr.write(f"エラー: {e}\n")
        return 1

    print(tr("persistent.header", name=result.persona_name))
    print()

    # 1) config.yaml ブロック / 自動書き込み
    if "config" in result.skipped:
        print(tr("persistent.config_skipped", reason=result.skipped["config"]))
    elif result.config_write_result is not None:
        cwr = result.config_write_result
        action = "persistent.config_updated" if not cwr.created else "persistent.config_written"
        print(tr(action, path=cwr.config_path, name=cwr.persona_name))
        if cwr.backup_path:
            print(tr("persistent.config_backup", path=cwr.backup_path))
    elif result.config_yaml_block:
        print(tr("persistent.config_label"))
        print("---")
        print(result.config_yaml_block)
        print("---")
        if args.config_yaml_output:
            print(tr("persistent.config_yaml_saved", path=args.config_yaml_output))
    print()

    # 2) SOUL.md 書き出し
    if "soul" in result.skipped:
        print(tr("persistent.soul_skipped", reason=result.skipped["soul"]))
    elif result.soul_result is not None:
        print(
            tr(
                "persistent.soul_written",
                path=result.soul_result.output_path,
                weight=result.soul_result.weight.value,
                lang=result.soul_result.lang,
            )
        )

    # 3) --apply: hermes config set agent.personality <name>
    if result.apply_result is not None:
        if result.apply_result == "ok":
            print(tr("persistent.apply_ok", name=result.persona_name))
        else:
            print(tr("persistent.apply_failed", reason=result.apply_result), file=sys.stderr)

    print()
    if result.config_write_result is not None:
        print(tr("persistent.footer_auto_config"))
    else:
        print(tr("persistent.footer"))
    return 0


def _cmd_persistent_target(args: argparse.Namespace, names: list[str]) -> int:
    """Hermes 以外のターゲット (Claude Code / Codex / Cursor / Gemini) への書き出し。"""
    # Hermes 専用フラグが指定されていれば注意喚起 (無視する)
    if args.auto_config or args.apply:
        print(tr("persistent.target_hermes_flags_ignored", target=args.target), file=sys.stderr)

    try:
        result = write_target(
            args.target,
            names,
            weight=args.weight,
            path=args.target_output,
            global_=args.global_target,
            force=args.force,
        )
    except (FileExistsError, FileNotFoundError, ValueError, KeyError) as e:
        sys.stderr.write(f"エラー: {e}\n")
        return 1

    action = "persistent.target_written" if result.created else "persistent.target_updated"
    print(tr(action, target=result.target, path=result.output_path))
    print()
    print(tr("persistent.target_footer", target=result.target, path=result.output_path))
    return 0


def _cmd_update(args: argparse.Namespace) -> int:
    """公開属性データ (attributes/ + schema/) を GitHub から取得して更新する。"""
    from hersona.core.paths import data_cache_root
    from hersona.core.update import (
        UpdateError,
        archive_url,
        clear_data_cache,
        update_data,
    )

    if args.clear:
        removed = clear_data_cache()
        if removed:
            print(tr("update.cleared", dirs=", ".join(removed), dest=data_cache_root()))
        else:
            print(tr("update.clear_none"))
        return 0

    ref = args.ref or "main"
    if args.dry_run:
        print(tr("update.dry_run", url=archive_url(ref), dest=data_cache_root()))
        return 0

    print(tr("update.fetching", ref=ref))
    try:
        result = update_data(ref)
    except UpdateError as e:
        print(f"{tr('error.prefix')}{e}", file=sys.stderr)
        return 1

    print(
        tr(
            "update.done",
            attrs=result.attribute_files,
            ref=result.ref,
            dest=result.dest,
        )
    )
    print(tr("update.hint"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
