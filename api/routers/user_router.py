from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import JSONResponse

from api.deps import UserRepositoryDepends
from db.models import User
from db.repository.user_repository import UserRepository

user_router = APIRouter(prefix="/user", tags=["user"])


class AddUserSchema(BaseModel):
    tg_user_id: str


class RegisterUserSchema(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    phone: str


@user_router.post("/")
async def add_user(
        body: AddUserSchema,
        user_repository: UserRepository = UserRepositoryDepends,
):
    try:
        user = User(
            tg_user_id=body.tg_user_id
        )
        await user_repository.add(user)
        return JSONResponse("add user", status_code=200)
    except Exception as e:
        print(e)
        return JSONResponse("user has already existed", status_code=208)


@user_router.get("/{user_id}")
async def get_user(
        user_id: str,
        user_repository: UserRepository = UserRepositoryDepends,
) -> Optional[User]:
    try:
        user: User = await user_repository.get(user_id)

        return user
    except Exception as e:
        print(e)
        return JSONResponse("user does not exist", status_code=208)


@user_router.post("/register")
async def register(
        body: RegisterUserSchema,
        user_repository: UserRepository = UserRepositoryDepends,
):
    try:
        user: User = await user_repository.get(body.user_id)
        user.phone = body.phone
        user.first_name = body.first_name
        user.last_name = body.last_name

        await user_repository.uow.commit()

        return JSONResponse("user has been registered", status_code=200)
    except Exception as e:
        print(e)
        return JSONResponse("user has already been registered", status_code=208)
