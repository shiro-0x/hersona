"""hersona MCP サーバーの配線 (mcp SDK への薄い殻)。

``mcp`` は任意依存 (``pip install "hersona[mcp]"``)。本モジュールは ``build_server()``
が呼ばれた時点で初めて ``mcp`` を lazy import するため、未インストールでも
``import hersona.mcp.server`` 自体は失敗しない (ツールロジックは tools.py 側で
テスト可能)。

エントリポイント: ``hersona-mcp`` (= ``hersona.mcp.server:main``) で stdio サーバーを起動。
"""
from __future__ import annotations

from hersona.mcp import tools

_INSTALL_HINT = (
    "the 'mcp' package is required for the hersona MCP server. "
    'Install it with: pip install "hersona[mcp]"'
)


def build_server():
    """FastMCP サーバーを構築し、hersona ツールを登録して返す。

    ``mcp`` 未インストールなら導入手順付きの ``RuntimeError`` を送出する。
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:  # pragma: no cover - exercised via the absent-mcp test path
        raise RuntimeError(_INSTALL_HINT) from e

    server = FastMCP("hersona")

    @server.tool()
    def list_attributes() -> dict:
        """List available hersona attributes grouped by category (public + user)."""
        return tools.list_attributes()

    @server.tool()
    def show_attribute(name: str) -> dict:
        """Show one attribute's details (display name, description, traits, relations)."""
        return tools.show_attribute(name)

    @server.tool()
    def blend(names: list[str], weight: str = "moderate") -> dict:
        """Blend attributes into a system-prompt injection block; reports conflicts."""
        return tools.blend(names, weight=weight)

    @server.tool()
    def export(names: list[str], weight: str = "moderate", fmt: str = "json") -> str:
        """Export a blend as json / messages / markdown for other agent frameworks."""
        return tools.export(names, weight=weight, fmt=fmt)

    @server.tool()
    def recommend_blend(
        answers: dict[str, int], top: int = 1, export_format: str | None = None
    ) -> dict:
        """Recommend a blend from diagnostic-quiz answers ({question_id: option_index}).

        Pass export_format (json / messages / markdown / openai_assistants /
        langchain_system_message) to also get the blend exported in that format
        under the "export" key — no need to re-enter the names into export.
        """
        return tools.recommend_blend(answers, top=top, export_format=export_format)

    @server.tool()
    def compatibility(name: str | None = None) -> dict:
        """Return the compatibility matrix, or one attribute's conflicts/compatibles."""
        return tools.compatibility(name)

    return server


def main() -> None:
    """``hersona-mcp`` エントリ: stdio トランスポートで MCP サーバーを起動する。"""
    build_server().run()


if __name__ == "__main__":
    main()
