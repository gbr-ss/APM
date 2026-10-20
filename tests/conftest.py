import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_admin, get_usuario_logado, get_usuario_opcional
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db_session_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def cliente(db_session_test):
    def get_db_teste():
        yield db_session_test

    def usuario_falso():
        return {"sub": "teste@aapm.com", "nome": "Admin Teste", "role": "admin", "id": 1}

    app.dependency_overrides[get_db] = get_db_teste
    app.dependency_overrides[get_usuario_logado] = usuario_falso
    app.dependency_overrides[get_admin] = usuario_falso
    app.dependency_overrides[get_usuario_opcional] = usuario_falso

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cliente_sem_autenticacao(db_session_test):
    def get_db_teste():
        yield db_session_test

    app.dependency_overrides[get_db] = get_db_teste

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
