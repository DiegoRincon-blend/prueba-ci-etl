import subprocess
import sys


def test_help_explains_status():
    result = subprocess.run(
        [sys.executable, "-m", "agente_cognitivo_ingestion.main", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "pendiente de implementación" in result.stdout


def test_execution_fails_until_implemented():
    result = subprocess.run(
        [sys.executable, "-m", "agente_cognitivo_ingestion.main"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "aún no está implementada" in result.stderr
