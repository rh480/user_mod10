import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session
import importlib
import sys

DATABASE_MODULE = "app.database"

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock the settings.DATABASE_URL before app.database is imported."""
    mock_url = "postgresql://user:password@localhost:5432/test_db"
    mock_settings = MagicMock()
    mock_settings.DATABASE_URL = mock_url
    # Ensure 'app.database' is not loaded
    if DATABASE_MODULE in sys.modules:
        del sys.modules[DATABASE_MODULE]
    # Patch settings in 'app.database'
    monkeypatch.setattr(f"{DATABASE_MODULE}.settings", mock_settings)
    return mock_settings

def reload_database_module():
    """Helper function to reload the database module after patches."""
    if DATABASE_MODULE in sys.modules:
        del sys.modules[DATABASE_MODULE]
    return importlib.import_module(DATABASE_MODULE)

def test_base_declaration(mock_settings):
    """Test that Base is an instance of declarative_base."""
    database = reload_database_module()
    Base = database.Base
    assert isinstance(Base, database.declarative_base().__class__)

def test_get_engine_success(mock_settings):
    """Test that get_engine returns a valid engine."""
    database = reload_database_module()
    engine = database.get_engine()
    assert isinstance(engine, Engine)

def test_get_engine_failure(mock_settings):
    """Test that get_engine raises an error if the engine cannot be created."""
    database = reload_database_module()
    with patch("app.database.create_engine", side_effect=SQLAlchemyError("Engine error")):
        with pytest.raises(SQLAlchemyError, match="Engine error"):
            database.get_engine()

def test_get_sessionmaker(mock_settings):
    """Test that get_sessionmaker returns a valid sessionmaker."""
    database = reload_database_module()
    engine = database.get_engine()
    SessionLocal = database.get_sessionmaker(engine)
    assert isinstance(SessionLocal, sessionmaker)


def test_get_db_yields_session_and_closes_it():
    """get_db should yield a session and close it when the generator finishes."""
    database = importlib.import_module("app.database")
    mock_session = MagicMock()

    with patch.object(database, "SessionLocal", return_value=mock_session):
        gen = database.get_db()
        assert next(gen) is mock_session
        mock_session.close.assert_not_called()
        with pytest.raises(StopIteration):
            next(gen)

    mock_session.close.assert_called_once()


def test_get_db_closes_session_on_error():
    """The session must be closed even if the caller raises an exception."""
    database = importlib.import_module("app.database")
    mock_session = MagicMock()

    with patch.object(database, "SessionLocal", return_value=mock_session):
        gen = database.get_db()
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("boom"))

    mock_session.close.assert_called_once()