from pathlib import Path

import uvicorn

from app.bootstrap import create_app
from app.common.settings.web import RunMode

ENVS_DIR = Path(__file__).resolve().parents[2] / 'run' / '.envs'
app, web_settings = create_app(env_name= str(ENVS_DIR / '.dev.env'))

if __name__ == '__main__':
    uvicorn.run(
        "app.main:app",
        host=web_settings.HTTP_HOST,
        port=web_settings.HTTP_PORT,
        reload=True if web_settings.RUN_MODE == RunMode.DEV else False,
        access_log=False,
    )