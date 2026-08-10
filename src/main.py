import inspect

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.credentials_encryption import CredentialsEncryptionService
from helpers.config import get_settings
from routes import base, tasks
from routes.auth import auth_router
from routes.database_connections import database_connections_router
from routes.files import files_router
from routes.projects import projects_router
from routes.roles import roles_router
from routes.search import search_router
from routes.user_roles import user_roles_router
from routes.users import users_router
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from stores.vectordb.VectorDBProviderFactory import (
    VectorDBProviderFactory,
)
from utils.llm_error_middleware import setup_llm_error_handling
from utils.metrics import setup_metrics


app = FastAPI()


async def startup_span() -> None:
    settings = get_settings()
    app.credentials_encryption_service = (
        CredentialsEncryptionService(
            settings.DATABASE_CREDENTIALS_ENCRYPTION_KEY
        )
    )
    print("Credentials encryption service initialized")


    app.db_engine = create_async_engine(
        settings.POSTGRES_URL,
        echo=False,
        pool_pre_ping=True,
    )

    app.db_client = sessionmaker(
        bind=app.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with app.db_client() as session:
        await session.execute(text("SELECT 1"))

    print("PostgreSQL connected successfully")

    llm_provider_factory = LLMProviderFactory(settings)

    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings,
        db_client=app.db_client,
    )

    app.generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )

    if app.generation_client is None:
        raise RuntimeError(
            "Generation provider not supported: "
            f"{settings.GENERATION_BACKEND}"
        )

    app.generation_client.set_generation_model(
        model_id=settings.GENERATION_MODEL_ID
    )

    print("Generation client initialized")

    # =========================
    # Embedding client
    # =========================
    app.embedding_client = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEND
    )

    if app.embedding_client is None:
        raise RuntimeError(
            "Embedding provider not supported: "
            f"{settings.EMBEDDING_BACKEND}"
        )

    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    print("Embedding client initialized")


    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )

    if app.vectordb_client is None:
        raise RuntimeError(
            "Vector DB provider not supported: "
            f"{settings.VECTOR_DB_BACKEND}"
        )


    connect_result = app.vectordb_client.connect()
    if inspect.isawaitable(connect_result):
        await connect_result

    print("Vector DB client initialized")

    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

    print("Template parser initialized")


async def shutdown_span() -> None:

    if (
        hasattr(app, "vectordb_client")
        and app.vectordb_client
    ):
        disconnect_result = app.vectordb_client.disconnect()
        if inspect.isawaitable(disconnect_result):
            await disconnect_result


    if hasattr(app, "db_engine") and app.db_engine:
        await app.db_engine.dispose()

    print("PostgreSQL connection closed")
    print("Vector DB connection closed")


app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)

setup_metrics(app)
setup_llm_error_handling(app)

app.include_router(base.base_router)
app.include_router(tasks.tasks_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(user_roles_router)
app.include_router(projects_router)
app.include_router(files_router)
app.include_router(search_router)
app.include_router(database_connections_router)
