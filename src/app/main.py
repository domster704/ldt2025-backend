import uvicorn

from app.bootstrap import create_app
from app.common.settings import http_server_settings, app_settings, RunMode

app = create_app()

if __name__ == '__main__':
    app
    uvicorn.run(
        "app.main:app",
        host=http_server_settings.http_host,
        port=http_server_settings.http_port,
        reload=app_settings.run_mode == RunMode.DEV,
        access_log=False,
    )