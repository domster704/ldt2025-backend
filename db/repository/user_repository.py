from typing import Optional

from db.models import User
from db.repository.repository import BaseRepository, UnitOfWork


class UserRepository(BaseRepository[User]):
    async def get(self, user_id: str = None, **kwargs) -> Optional[User]:
        return await super().get(reference=user_id, field_search=User.tg_user_id.name)