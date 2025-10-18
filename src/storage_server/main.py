import uvicorn

from bootstrap import bootstrap
from settings import RunMode

fastapi_app, settings = bootstrap()

uvicorn.run(
    fastapi_app,
    host=settings['host'],
    port=settings['port'],
    reload=settings['run_mode'] == RunMode.DEV,
    access_log=False,
)