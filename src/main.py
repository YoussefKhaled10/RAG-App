from fastapi import FastAPI
from routes import base, data, nlp , tasks
from routes.auth import auth_router
from routes.users import users_router
from routes.roles import roles_router
from routes.user_roles import user_roles_router
from routes.projects import projects_router
from routes.files import files_router
from routes.search import search_router
from helpers.config import get_settings

from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from utils.metrics import setup_metrics

import inspect

app = FastAPI()

setup_metrics(app)


async def startup_span():
    settings = get_settings()

    # =========================
    # PostgreSQL connection
    # =========================
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

    # Test PostgreSQL connection early
    async with app.db_client() as session:
        await session.execute(text("SELECT 1"))

    print("PostgreSQL connected successfully")

    # =========================
    # LLM Factory
    # =========================
    llm_provider_factory = LLMProviderFactory(settings)

    # =========================
    # Vector DB Factory
    # =========================
    # IMPORTANT:
    # PGVectorProvider needs the SQLAlchemy async sessionmaker.
    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings,
        db_client=app.db_client,
    )

    # =========================
    # Generation client
    # =========================
    app.generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )

    if app.generation_client is None:
        raise Exception(
            f"Generation provider not supported: {settings.GENERATION_BACKEND}"
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
        raise Exception(
            f"Embedding provider not supported: {settings.EMBEDDING_BACKEND}"
        )

    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    print("Embedding client initialized")

    # =========================
    # Vector DB client
    # =========================
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )

    if app.vectordb_client is None:
        raise Exception(
            f"Vector DB provider not supported: {settings.VECTOR_DB_BACKEND}"
        )

    # PGVectorProvider.connect() is async.
    # QdrantProvider may be sync.
    connect_result = app.vectordb_client.connect()

    if inspect.isawaitable(connect_result):
        await connect_result

    print("Vector DB client initialized")

    # =========================
    # Template Parser
    # =========================
    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

    print("Template parser initialized")


async def shutdown_span():
    # =========================
    # Vector DB disconnect
    # =========================
    if hasattr(app, "vectordb_client") and app.vectordb_client:
        disconnect_result = app.vectordb_client.disconnect()

        if inspect.isawaitable(disconnect_result):
            await disconnect_result

    # =========================
    # PostgreSQL disconnect
    # =========================
    if hasattr(app, "db_engine") and app.db_engine:
        await app.db_engine.dispose()

    print("PostgreSQL connection closed")
    print("Vector DB connection closed")


app.on_event("startup")(startup_span)
app.on_event("shutdown")(shutdown_span)

app.include_router(base.base_router)
""" app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
app.include_router(upload_index.upload_index_router) """
app.include_router(tasks.tasks_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(user_roles_router)
app.include_router(projects_router)
app.include_router(files_router)    
app.include_router(search_router)
