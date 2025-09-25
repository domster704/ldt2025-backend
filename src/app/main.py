from pathlib import Path

import uvicorn

from app.bootstrap import create_app
from app.common.settings.web import RunMode
from common.settings.web import app_settings, http_server_settings

ENVS_DIR = Path(__file__).resolve().parents[2] / 'run' / '.envs'
app = create_app(env_name= str(ENVS_DIR / '.dev.env'))

if __name__ == '__main__':
    app
    uvicorn.run(
        "app.main:app",
        host=http_server_settings.http_host,
        port=http_server_settings.http_port,
        reload=app_settings.run_mode == RunMode.DEV,
        access_log=False,
    )