import pathlib
import sys
import pytest
from fastapi.testclient import TestClient

# быстрый фикс для импорта main.py
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import main


class RedisMock:
    def __init__(self):
        self._store: dict[str, dict] = {}

    async def get(self, phone):
        key = str(phone)
        return self._store.get(key)

    async def create(self, customer_addr) -> bool:
        key = str(customer_addr.phone)
        if key in self._store:
            return False
        self._store[key] = {"phone": key, "address": customer_addr.address}
        return True

    async def update(self, customer_addr) -> bool:
        key = str(customer_addr.phone)
        if key not in self._store:
            return False
        self._store[key]["address"] = customer_addr.address
        return True

    async def delete(self, phone) -> bool:
        key = str(phone)
        return self._store.pop(key, None) is not None


# Применяем Mock Redis клиент
@pytest.fixture(autouse=True)
def use_test_store():
    main.redis_client = RedisMock()
    yield

# Пробрасываем клиент для тестов
@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c
