import contextlib
import os
from typing import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection,
    AsyncSession,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


class Config:
    DB_CONFIG = "postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}".format(
        DB_USER=os.getenv("DB_USER", "postgres"),
        DB_PASSWORD=os.getenv("DB_PASS", "postgres"),
        DB_HOST=os.getenv("DB_HOST", "127.0.0.1"),
        DB_PORT=os.getenv("DB_PORT", "5432"),
        DB_NAME=os.getenv("DB_NAME", "postgres"),
    )
    DB_SYNC_CONFIG = "postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}".format(
        DB_USER=os.getenv("DB_USER", "postgres"),
        DB_PASSWORD=os.getenv("DB_PASS", "postgres"),
        DB_HOST=os.getenv("DB_HOST", "127.0.0.1"),
        DB_PORT=os.getenv("DB_PORT", "5432"),
        DB_NAME=os.getenv("DB_NAME", "postgres"),
    )


config = Config

Base = declarative_base()


class DatabaseSessionManager:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker | None = None

    def init(self, host: str):
        self._engine = create_async_engine(host, echo=False)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine, expire_on_commit=False)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Used for testing
    async def create_all(self, connection: AsyncConnection):
        await connection.run_sync(Base.metadata.create_all)

    async def drop_all(self, connection: AsyncConnection):
        await connection.run_sync(Base.metadata.drop_all)


sessionmanager = DatabaseSessionManager()

engine = create_async_engine(config.DB_CONFIG)


async def get_db():
    async with sessionmanager.session() as session:
        yield session


sync_engine = create_engine(Config.DB_SYNC_CONFIG)
SyncSession = sessionmaker(bind=sync_engine)
