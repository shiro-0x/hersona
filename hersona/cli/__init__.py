"""hersona CLI/TUI 殻 (ROADMAP: 対話 CLI/TUI)。

core ロジック (compatibility / authoring / recommend / attach) の薄い殻。
エントリポイントは `hersona.cli.main`。
"""

from hersona.cli.app import main

__all__ = ["main"]
