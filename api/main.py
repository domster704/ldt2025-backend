import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.routers.security_router import security_router, AuthMiddleware
from api.routers.user_router import user_router
from settings import settings

app = FastAPI()
app.include_router(security_router)
app.include_router(user_router)

app.add_middleware(SessionMiddleware, secret_key=settings.security.secretkey.get_secret_value(),
                   session_cookie="session_id")
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
