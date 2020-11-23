
from app import create_app
import pytest
import os
from database import engine, db_session

@pytest.fixture
def test_app():
    app = create_app().app
    
    yield app, app.test_client()

    db_session.remove()
    os.remove('./user.db')