from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_initial_pages_do_not_load_analysis_dependencies(tmp_path) -> None:
    """Protect boot, homepage and analysis setup from expensive eager imports."""
    script = r'''
import importlib.abc
import socket
import sys
from unittest.mock import patch

blocked = {"matplotlib", "pandas", "pptx", "anthropic", "src.charts", "src.ppt_exporter", "src.analyzer", "src.claude_client"}

class BlockHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in blocked):
            raise AssertionError("Startup imported " + fullname)

sys.meta_path.insert(0, BlockHeavyImports())
from streamlit.testing.v1 import AppTest
with patch.object(socket.socket, "connect", side_effect=AssertionError("Initial pages must not make network calls")):
    app = AppTest.from_file("app.py", default_timeout=20).run()
    assert not app.exception, [item.message for item in app.exception]
    next(button for button in app.button if button.label == "进入首页").click().run()
    assert not app.exception, [item.message for item in app.exception]
    assert any(button.label == "单市场分析" for button in app.button)
    app.button(key="navbtn_single").click().run()
    assert not app.exception, [item.message for item in app.exception]
    assert any(item.label == "游戏名称" for item in app.text_input)
    assert not any(name in sys.modules for name in blocked)
print("Boot, homepage and analysis setup rendered without heavy dependencies or network")
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "APP_ACCESS_PASSWORD": "", "MPLCONFIGDIR": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
