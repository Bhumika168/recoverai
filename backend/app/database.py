from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from app.logging_config import logger


class Base(DeclarativeBase):
    pass


# Build database engine
# Handles both postgresql+asyncpg:// and sqlite+aiosqlite:///
engine_kwargs = {"echo": settings.DB_ECHO}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = getattr(settings, "DB_POOL_SIZE", 20)
    engine_kwargs["max_overflow"] = getattr(settings, "DB_MAX_OVERFLOW", 10)
    engine_kwargs["pool_recycle"] = getattr(settings, "DB_POOL_RECYCLE", 3600)
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables in the database if they do not exist, and auto-migrate missing columns."""
    logger.info("Initializing database schema...")
    # Import all models to ensure they are registered with Base.metadata
    import app.models  # noqa: F401
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Handle SQLite column additions safely if tables already existed
        if settings.DATABASE_URL.startswith("sqlite"):
            try:
                # organizations columns
                org_info = await conn.execute(text("PRAGMA table_info(organizations)"))
                org_cols = {row[1] for row in org_info.fetchall()}
                if "environment" not in org_cols:
                    await conn.execute(text("ALTER TABLE organizations ADD COLUMN environment VARCHAR(32) DEFAULT 'Production'"))

                # recovery_cases columns
                rc_info = await conn.execute(text("PRAGMA table_info(recovery_cases)"))
                existing_cols = {row[1] for row in rc_info.fetchall()}
                if "campaign_id" not in existing_cols:
                    await conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN campaign_id VARCHAR(36)"))
                if "messages_sent_count" not in existing_cols:
                    await conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN messages_sent_count INTEGER DEFAULT 0"))
                
                # campaigns columns
                cmp_info = await conn.execute(text("PRAGMA table_info(campaigns)"))
                cmp_cols = {row[1] for row in cmp_info.fetchall()}
                if "organization_id" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN organization_id VARCHAR(36)"))
                if "status" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN status VARCHAR(32) DEFAULT 'ACTIVE'"))
                if "recovery_type" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN recovery_type VARCHAR(64) DEFAULT 'FAILED_PAYMENT'"))
                if "channels_list" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN channels_list JSON"))
                if "min_amount" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN min_amount FLOAT DEFAULT 0.0"))
                if "max_amount" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN max_amount FLOAT DEFAULT 1000000.0"))
                if "max_recovery_attempts" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN max_recovery_attempts INTEGER DEFAULT 3"))
                if "retry_delay_hours" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN retry_delay_hours INTEGER DEFAULT 24"))
                if "escalation_rules" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN escalation_rules JSON"))
                if "enrolled_cases_count" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN enrolled_cases_count INTEGER DEFAULT 0"))
                if "messages_sent_count" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN messages_sent_count INTEGER DEFAULT 0"))
                if "actions_executed_count" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN actions_executed_count INTEGER DEFAULT 0"))
                if "recovered_amount" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN recovered_amount FLOAT DEFAULT 0.0"))
                if "recovery_rate" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN recovery_rate FLOAT DEFAULT 0.0"))
                if "last_activity_at" not in cmp_cols:
                    await conn.execute(text("ALTER TABLE campaigns ADD COLUMN last_activity_at DATETIME"))
            except Exception as e:
                logger.warning(f"Schema migration note: {e}")

    logger.info("Database schema initialized successfully.")
