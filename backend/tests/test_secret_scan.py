from pathlib import Path
import subprocess
import sys


def test_frontend_does_not_contain_mappls_server_secrets():
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_no_mappls_secrets.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
