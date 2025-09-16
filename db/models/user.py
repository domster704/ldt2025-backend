from typing import Optional, List

from sqlalchemy import Column, JSON
from sqlalchemy.orm import Mapped, relationship
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True, nullable=False)
    tg_user_id: str = Field(nullable=False, unique=True)
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)

    notifications: bool = Field(default=False)
    isPassedOnboarding: bool = Field(default=False)

    token: Optional[str] = Field(default=None, sa_column=Column(JSON))

    # products: Mapped[List["UsersProductsLinks"]] = Relationship(
    #     sa_relationship=relationship(
    #         "Product",
    #         secondary=UsersProductsLinks.__table__,
    #         back_populates='users',
    #         passive_deletes=True
    #     )
    # )
