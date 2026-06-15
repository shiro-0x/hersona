"""エージェント／ツール別の永続化ターゲット (CLAUDE.md / AGENTS.md / .cursorrules / GEMINI.md ...)。

`hersona persistent` は既定で Hermes の `~/.hermes/SOUL.md` に書き出すが、人格本文は
ただの Markdown なので、他ツールの「起動時に自動読み込みされる規約ファイル」へ
書き出すだけで同じ永続化が実現できる。本モジュールはその出力先と見出しの差分のみを
定義し、本文生成は `soul.render_soul` を再利用する。

サポートするターゲット:
- ``claude``  : ``CLAUDE.md`` (プロジェクト) / ``~/.claude/CLAUDE.md`` (--global)
- ``codex``   : ``AGENTS.md`` (汎用標準。Codex CLI ほか多数が対応)
- ``cursor``  : ``.cursorrules`` (プロジェクト)
- ``gemini``  : ``GEMINI.md`` (プロジェクト) / ``~/.gemini/GEMINI.md`` (--global)

注: ``hermes`` は SOUL.md + config.yaml + ``hermes config set`` の専用経路を持つため、
このレジストリには含めず ``persistent`` 側で従来どおり扱う。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hersona.core.soul import render_soul
from hersona.core.weight import WeightLevel


@dataclass(frozen=True)
class TargetSpec:
    """永続化ターゲットの定義。"""

    name: str
    description: str
    filename: str  # プロジェクト直下 / グローバルディレクトリ共通のファイル名
    home_subdir: tuple[str, ...] | None  # --global 時のホーム配下サブディレクトリ
    title: str  # 出力 Markdown の先頭見出し
    intro: tuple[str, ...]  # 見出し直下の blockquote 行

    def resolve_path(self, *, global_: bool = False, cwd: Path | None = None) -> Path:
        """書き出し先パスを解決する。

        Args:
            global_: True ならホーム配下 (home_subdir) に書く
            cwd: プロジェクト基準ディレクトリ (省略時は現在の作業ディレクトリ)

        Returns:
            書き出し先パス
        """
        if global_:
            if self.home_subdir is None:
                # グローバル位置を持たないターゲットはホーム直下に置く
                return Path.home() / self.filename
            base = Path.home()
            for part in self.home_subdir:
                base = base / part
            return base / self.filename
        root = cwd if cwd is not None else Path.cwd()
        return Path(root) / self.filename


# 共通イントロ (ツール非依存)
def _intro(tool_label: str) -> tuple[str, ...]:
    return (
        f"> {tool_label} が起動時に読み込む人格定義 (hersona 生成)。",
        "> 含まれる 4 要素: name / personality / tone / behavioral guidelines。",
        "> このファイルが読まれている間、エージェントはこの人格として応答する。",
    )


TARGETS: dict[str, TargetSpec] = {
    "claude": TargetSpec(
        name="claude",
        description="Claude Code (CLAUDE.md)",
        filename="CLAUDE.md",
        home_subdir=(".claude",),
        title="# Persona (hersona)",
        intro=_intro("Claude Code"),
    ),
    "codex": TargetSpec(
        name="codex",
        description="Codex / AGENTS.md (generic standard)",
        filename="AGENTS.md",
        home_subdir=(".codex",),
        title="# Persona (hersona)",
        intro=_intro("AGENTS.md 対応エージェント"),
    ),
    "cursor": TargetSpec(
        name="cursor",
        description="Cursor (.cursorrules)",
        filename=".cursorrules",
        home_subdir=None,
        title="# Persona (hersona)",
        intro=_intro("Cursor"),
    ),
    "gemini": TargetSpec(
        name="gemini",
        description="Gemini CLI (GEMINI.md)",
        filename="GEMINI.md",
        home_subdir=(".gemini",),
        title="# Persona (hersona)",
        intro=_intro("Gemini CLI"),
    ),
}

# `agents` を `codex` のエイリアスとして許容
TARGET_ALIASES = {"agents": "codex"}


def available_targets() -> list[str]:
    """利用可能なターゲット名 (エイリアス除く) を返す。"""
    return list(TARGETS)


def resolve_target(name: str) -> TargetSpec:
    """ターゲット名 (エイリアス含む) から TargetSpec を返す。

    Raises:
        KeyError: 未知のターゲット名
    """
    key = TARGET_ALIASES.get(name, name)
    if key not in TARGETS:
        raise KeyError(
            f"未知のターゲット: '{name}'。"
            f"利用可能: {', '.join([*TARGETS, *TARGET_ALIASES])}"
        )
    return TARGETS[key]


@dataclass
class TargetWriteResult:
    """ターゲットファイル書き出し結果。"""

    target: str
    output_path: Path
    content: str
    created: bool  # True = 新規作成 / False = 上書き


def render_for_target(
    target: str,
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    matrix=None,
    public_root=None,
    user_root=None,
) -> str:
    """ターゲット向けの人格 Markdown 文字列を生成する。

    本文は `soul.render_soul` を再利用し、見出し/イントロのみターゲット仕様に置換する。
    """
    spec = resolve_target(target)
    return render_soul(
        names,
        weight=weight,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
        title=spec.title,
        intro=list(spec.intro),
        agent_label=None,  # 「正式名称: Hermes Agent」行は Hermes 専用なので省略
    )


def write_target(
    target: str,
    names: list[str],
    *,
    weight: str | WeightLevel = WeightLevel.MODERATE,
    path: str | Path | None = None,
    global_: bool = False,
    force: bool = False,
    matrix=None,
    public_root=None,
    user_root=None,
) -> TargetWriteResult:
    """人格 Markdown をターゲットファイルに書き出す。

    Args:
        target: ターゲット名 (claude / codex / cursor / gemini, または agents)
        names: 適用する属性名
        weight: 強度
        path: 出力パスの明示指定 (省略時はターゲット規定パス)
        global_: True ならホーム配下に書く (path 未指定時のみ有効)
        force: 既存ファイルがあっても上書きする
        matrix / public_root / user_root: 属性解決 (テスト用)

    Returns:
        TargetWriteResult

    Raises:
        KeyError: 未知のターゲット
        FileExistsError: 既存ファイルがあり force=False
        FileNotFoundError: 親ディレクトリが存在せず作成もできない場合
        ValueError: blend が空 / conflict 検出
    """
    spec = resolve_target(target)
    if path is not None:
        output_path = Path(path)
    else:
        output_path = spec.resolve_path(global_=global_)

    content = render_for_target(
        target,
        names,
        weight=weight,
        matrix=matrix,
        public_root=public_root,
        user_root=user_root,
    )

    created = not output_path.exists()
    if not created and not force:
        raise FileExistsError(
            f"{output_path} は既に存在します。上書きするには --force を使用してください。"
        )

    # 親ディレクトリは必要なら作成する (グローバル ~/.claude 等)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    return TargetWriteResult(
        target=spec.name,
        output_path=output_path,
        content=content,
        created=created,
    )
