from unittest.mock import MagicMock

import pytest

from faultline_backend.config import Settings
from faultline_backend.storage import Database, Store


@pytest.fixture
def settings():
    # Never use a developer's real API key or dotenv settings during tests.
    return Settings(_env_file=None, openai_api_key=None)


@pytest.fixture
def mocked_store(settings):
    """Tests only: exercise the real storage adapter/trace against a mocked driver."""
    database = MagicMock(spec=Database)
    database.settings = settings
    graph = database.client.select_graph.return_value
    store = Store(database, "unit")
    return store, graph
