import abc
from typing import TypeVar, List, Optional, Type, Generic, get_args, get_origin

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import AsyncSessionLocal
from ..models import SQLModel

ModelType = TypeVar("ModelType", bound=SQLModel)


class UnitOfWork:
    """Класс для управления единицей работы (Unit of Work) с базой данных.

    Этот класс предоставляет контекстный менеджер для работы с асинхронной сессией SQLAlchemy.
    Он автоматически управляет открытием и закрытием сессии, а также обработкой транзакций.

    Attributes:
        session (AsyncSession): Асинхронная сессия SQLAlchemy.
    """

    def __init__(self):
        """Инициализирует экземпляр UnitOfWork."""
        self.session: AsyncSession = None

    async def __aenter__(self):
        """Открывает асинхронную сессию при входе в контекстный менеджер.

        Returns:
            UnitOfWork: Текущий экземпляр UnitOfWork.
        """
        self.session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает асинхронную сессию при выходе из контекстного менеджера.

        Args:
            exc_type: Тип исключения, если оно произошло.
            exc_val: Значение исключения, если оно произошло.
            exc_tb: Трассировка стека исключения, если оно произошло.
        """
        if self.session:
            await self.session.close()

    async def commit(self) -> bool:
        """Фиксирует изменения в базе данных.

        Returns:
            bool: True, если коммит выполнен успешно, иначе False.

        Raises:
            SQLAlchemyError: Если произошла ошибка при выполнении коммита.
        """
        try:
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise


class AbstractRepository(abc.ABC, Generic[ModelType]):
    """Абстрактный базовый класс для репозиториев.

    Этот класс определяет интерфейс для работы с базой данных, включая методы для добавления,
    получения, обновления и удаления объектов.

    Attributes:
        model (Type[ModelType]): Модель SQLModel, с которой работает репозиторий.
        uow (UnitOfWork): Единица работы для управления сессией.
    """

    def __init__(self, model: Type[ModelType], uow: UnitOfWork):
        """Инициализирует экземпляр AbstractRepository.

        Args:
            model (Type[ModelType]): Модель SQLModel.
            uow (UnitOfWork): Единица работы для управления сессией.
        """
        self.model = model
        self.uow = uow

    @abc.abstractmethod
    async def add(self, **kwargs) -> ModelType:
        """Добавляет объект в базу данных.

        Returns:
            ModelType: Добавленный объект.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, **kwargs) -> Optional[ModelType]:
        """Получает объект из базы данных.

        Returns:
            Optional[ModelType]: Найденный объект или None, если объект не найден.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all(self, **kwargs) -> List[ModelType]:
        """Получает все объекты из базы данных.

        Returns:
            List[ModelType]: Список всех объектов.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all_by_ids(self, **kwargs) -> List[ModelType]:
        """Возвращает все объекты, чьи `id` входят в переданный список.

        Returns:
            List[ModelType]: Список всех объектов.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, **kwargs) -> bool:
        """Удаляет объект из базы данных.

        Returns:
            bool: True, если удаление выполнено успешно, иначе False.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, **kwargs) -> ModelType:
        """Обновляет объект в базе данных.

        Returns:
            ModelType: Обновленный объект.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.
        """
        raise NotImplementedError


class BaseRepository(AbstractRepository[ModelType]):
    """Базовый универсальный репозиторий для работы с моделями SQLModel.
    https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.desc

    Этот класс реализует базовые CRUD-операции (создание, чтение, обновление, удаление)
    для работы с базой данных.

    Attributes:
        model (Type[ModelType]): Модель SQLModel, с которой работает репозиторий.
        uow (UnitOfWork): Единица работы для управления сессией.
    """

    def __init__(self, model: Type[ModelType] | None = None, uow: UnitOfWork = None):
        """Инициализирует экземпляр BaseRepository.

        Args:
            model (Type[ModelType]): Модель SQLModel.
            uow (UnitOfWork): Единица работы для управления сессией.
        """
        model_cls = model or self._model_class
        super().__init__(model_cls, uow)

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for base in cls.__orig_bases__:
            if get_origin(base) is BaseRepository:
                model_cls = get_args(base)[0]
                cls._model_class = model_cls

    async def add(self, model: ModelType, commit: bool = True, **kwargs) -> ModelType:
        """
        Добавляет объект в базу данных.

        Args:
            model (ModelType): Объект для добавления в базу данных.
            commit (bool): Если True — выполняется commit сразу, иначе — откладывается.

        Returns:
            ModelType: Добавленный объект.
        """
        self.uow.session.add(model)

        if commit:
            await self.uow.commit()
            await self.uow.session.refresh(model)

        return model

    async def get(self, reference: int = None, *, field_search: Optional[str] = "id", **kwargs) -> Optional[ModelType]:
        """Получает объект из базы данных по указанному полю.

        Args:
            reference (int, optional): Значение для поиска. По умолчанию None.
            field_search (str, optional): Поле для поиска. По умолчанию "id".

        Returns:
            Optional[ModelType]: Найденный объект или None, если объект не найден.

        Raises:
            ValueError: Если указанное поле не существует в модели.

        Notes:

        """
        if field_search is None:
            result = await self.uow.session.exec(select(self.model))
        else:
            if hasattr(self.model, field_search):
                result = await self.uow.session.exec(
                    select(self.model).where(getattr(self.model, field_search) == reference))
            else:
                raise ValueError(f"Field {field_search} does not exist in model {self.model}")
        return result.first()

    async def get_all(self, **kwargs) -> List[ModelType]:
        """Получает все объекты из базы данных.

        Returns:
            List[ModelType]: Список всех объектов.
        """
        result = await self.uow.session.exec(select(self.model))
        return result.all()

    async def get_all_by_ids(self, ids: List[int] | List[str]) -> List[ModelType]:
        """Возвращает все объекты, чьи `id` входят в переданный список.

        Args:
            ids: Список первичных ключей модели.

        Returns:
            list[ModelType]: Список найденных объектов (может быть пустым).
        """
        if not ids:
            return []

        stmt = select(self.model).where(self.model.id.in_(ids))
        result = await self.uow.session.exec(stmt)
        return result.all()

    async def delete(self, reference: int = None, **kwargs) -> bool:
        """Удаляет объект из базы данных по ID.

        Args:
            reference (int, optional): ID объекта для удаления. По умолчанию None.

        Returns:
            bool: True, если удаление выполнено успешно, иначе False.
        """
        obj: ModelType = await self.get(reference)
        if obj:
            await self.uow.session.delete(obj)
            return await self.uow.commit()
        return False

    async def update(self, model: ModelType, new_model: ModelType, **kwargs) -> ModelType:
        """Обновляет объект в базе данных.

        Args:
            model (ModelType): Объект для обновления.
            new_model (ModelType): Новые данные для объекта.

        Returns:
            ModelType: Обновленный объект.
        """
        if not model:
            return

        model_ = model
        for attr, value in new_model.__dict__.items():
            if hasattr(model_, attr) and attr != "_sa_instance_state":
                setattr(model_, attr, value)

        await self.uow.session.commit()
        return model_
