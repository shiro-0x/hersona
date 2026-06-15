"""hersona MCP サーバー (ROADMAP C / IMPROVEMENT_PLAN M3: hersona-mcp)。

core ロジックを薄く包む Model Context Protocol サーバー。Claude 等のエージェントが
`list / show / blend / recommend / export` を直接ツール呼び出しできるようにする。

- ``hersona.mcp.tools``  : 純粋ロジック (JSON 可搬な dict/str を返す)。``mcp`` 非依存でテスト可能。
- ``hersona.mcp.server`` : ``mcp`` SDK への薄い配線 (lazy import)。``hersona-mcp`` エントリ。
"""
