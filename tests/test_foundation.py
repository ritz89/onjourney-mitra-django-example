import os
import subprocess
import sys
from pathlib import Path


def test_health_check_reports_demo_mode(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "demo"}


def test_production_settings_reject_demo_mode():
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "ONJOURNEY_DEMO_MODE": "true",
            "SECRET_KEY": "test-only-secret",
            "ALLOWED_HOSTS": "mitra.example",
        }
    )

    result = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Demo mode cannot be enabled in production" in result.stderr
