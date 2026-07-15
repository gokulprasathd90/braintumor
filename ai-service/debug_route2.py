import os
os.environ["AI_SERVICE_ENV"] = "test"
os.environ["BCRYPT_ROUNDS"] = "4"

from fastapi.testclient import TestClient
from app.main import app
from app.security.dependencies import get_current_user, get_current_active_user, optional_auth
from app.security.auth import UserInDB
from app.security.roles import Role

MOCK_USER = UserInDB(
    user_id="mock-admin-id",
    username="admin",
    email="admin@test.local",
    hashed_password="",
    role=Role.ADMIN,
    is_active=True,
    is_locked=False,
    failed_login_count=0,
    locked_until=None
)

async def mock_user():
    return MOCK_USER

app.dependency_overrides[get_current_user] = mock_user
app.dependency_overrides[get_current_active_user] = mock_user
app.dependency_overrides[optional_auth] = mock_user

client = TestClient(app)

resp = client.post(
    '/api/v1/performance/benchmark/run',
    json={'n_inference': 2, 'n_preprocess': 3, 'n_cache': 5, 'batch_sizes': [2], 'background': False}
)
print('Status:', resp.status_code)
import json
try:
    print('Body:', json.dumps(resp.json(), indent=2))
except:
    print('Body:', resp.text[:2000])
