import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Async URL — used by FastAPI app at runtime
# asyncpg handles ssl differently — via connect_args, not the URL string
DATABASE_URL = os.getenv("DATABASE_URL", "")

ASYNC_DATABASE_URL = (
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    .replace("postgres://", "postgresql+asyncpg://")
    .split("?")[0]  # strips all query params — asyncpg gets them via connect_args
)

SYNC_DATABASE_URL = (
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://").replace(
        "postgres://", "postgresql+psycopg2://"
    )
    # keep ?sslmode=require for psycopg2 — it handles it fine in the URL
)

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    connect_args={"ssl": "require"},  # ssl passed here instead
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# def init_db():
#     Base.metadata.create_all(bind=engine)
