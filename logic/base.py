from datetime import datetime
from typing import TypeVar, Union, List, Type, Tuple, Sequence

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound="BaseModel")


class BaseModel:

    @classmethod
    async def create(cls: Type[T], session: AsyncSession, **kwargs) -> T:
        """
        Создание записи в базе данных.
        """
        new_record: T = cls(**kwargs)
        session.add(new_record)
        await session.commit()
        await session.refresh(new_record)
        return new_record

    @classmethod
    async def get(cls, session: AsyncSession, id: int) -> Union[dict, None]:
        """
        Функция получения записи из базы данных по ID
        :param session:
        :param id:
        :return:
        """
        record = await session.get(cls, id)
        if record:
            return record
        else:
            return None

    @classmethod
    async def update(
            cls, session: AsyncSession, id: int, data: dict
    ) -> Union[str, None]:
        """
        Функция обновления записи в базе данных
        :param session:
        :param id:
        :param data:
        :return:
        """
        record = await session.get(cls, id)
        if not record:
            return f"Record with id {id} does not exist"

        for key, value in data.items():
            if value is not None:
                setattr(record, key, value)

        try:
            await session.commit()
            await session.refresh(record)
        except IntegrityError as e:
            return "Error in updating record: " + str(e)

        return None

    @classmethod
    async def delete(cls, session: AsyncSession, id: int) -> Union[str, None]:
        """
        Функция удаления записи из базы данных
        :param session:
        :param id:
        :return:
        """
        record = await session.get(cls, id)
        if not record:
            return f"Record with id {id} does not exist"

        try:
            await session.delete(record)
            await session.commit()
        except Exception as e:
            return "Error in deleting record: " + str(e)

        return None

    @classmethod
    async def get_all(cls, session: AsyncSession) -> List[T]:
        """
        Функция получения всех записей из базы данных
        :param session:
        :return:
        """
        records = await session.execute(select(cls))
        return records.scalars().all()

    @classmethod
    async def get_by_kwargs(
            cls: Type[T],
            session: AsyncSession,
            multiple: bool = False,
            order_by: str = None,
            **kwargs,
    ) -> Union[List[T], T, None]:
        """
        Получение записи из базы данных по заданным параметрам.
        """
        stmt = select(cls).filter_by(**kwargs)
        if order_by:
            stmt = stmt.order_by(order_by)
        result = await session.execute(stmt)
        if multiple:
            return result.scalars().all()
        return result.scalars().first()

    @classmethod
    async def get_or_create(
            cls: Type[T], session: AsyncSession, **kwargs
    ) -> tuple[list[T], bool] | tuple[T, bool]:
        """
        Получение записи из базы данных по заданным параметрам или создание новой, если таковой не существует.
        """
        record = await cls.get_by_kwargs(session, **kwargs)
        if record:
            return record, False
        else:
            record = await cls.create(session, **kwargs)
            return record, True

    @classmethod
    async def get_all_count_by_period(
            cls: Type[T],
            session: AsyncSession,
            start_date: str = None,
            end_date: str = None,
    ) -> int:
        """
        Возвращает количество записей за период

        :param session: асинхронная сессия
        :param start_date: дата начала периода
        :param end_date: дата окончания периода

        :return: количество записей
        """
        # Если ни один из параметров не передан, возвращаем количество всех записей
        if not any([start_date, end_date]):
            count = await session.execute(
                select(func.count()).where(cls.id.isnot(None))
            )
        # Иначе возвращаем количество записей за указанный период
        else:
            start_date = (
                datetime.strptime(start_date + " 00:00:00", "%Y-%m-%d %H:%M:%S")
                if start_date
                else None
            )
            end_date = (
                datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
                if end_date
                else datetime.now()
            )
            try:
                if not start_date:
                    count = await session.execute(
                        select(func.count()).where(cls.timestamp <= end_date)
                    )
                else:
                    count = await session.execute(
                        select(func.count()).where(
                            cls.timestamp.between(start_date, end_date)
                        )
                    )
            except AttributeError:
                raise AttributeError("Model has no attribute 'timestamp'")
        return count.scalar()
