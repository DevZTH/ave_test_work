from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from pydantic_extra_types.phone_numbers import PhoneNumber
from redis import Redis
from os import getenv

REDIS_HOST = getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(getenv("REDIS_PORT", 6379))
REDIS_USERNAME = getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = getenv("REDIS_PASSWORD", "changeme123")
REDIS_DB = int(getenv("REDIS_DB", 0))
ENDPOINT_PREFIX = getenv("ENDPOINT_PREFIX", "/addr_by_phone")

app = FastAPI(
    title="Phone Address API",
    description="API для сорханения и получения адресов по номеру телефона",
    version="0.0.1",
    docs_url="/docs",)


class CustomerAddr(BaseModel):
    """
    Поля:
    - phone:номер телефона в международном формате (начиная c +) пример +7 111 222 33 44 (формат E.164 или RFC3966)
    - address: полная строка адреса (улица, дом, город и т.д.) от 10 до 255 символов
    """
    phone: PhoneNumber = Field(
        description="E.164 formatted phone number", example="+447911123456")

    # Тема с адресами обширная и довольно скользкая. Можно использовать готовые библиотеки для парсинга адресов, но они могут не покрывать все случаи.
    # а для серввиса доставки вообще хорошо бы хранить геометку, но это уже выходит за рамки текущего задания.
    # Так что ограничусь строкой с валидацией по минимальной и максимальной длине.
    address: str = Field(min_length=10, max_length=255,
                         description="Full postal address", example="г. Белгород, ул. Щорса, 123")


class SystemResponse(BaseModel):
    """Стандартный ответ системы для операций создания, обновления, удаления"""
    detail: str
    # потому что неплохо знать что именно было создано/обновлено/удалено или пошло не так
    customer_addr: CustomerAddr | None = None


class RedisWrapper(Redis):
    """Расширение Redis клиента CRUD для CustomerAddr"""
    # выбран вариант хранения без избыточного хранения структуры, т.е. ключ - номер телефона, значение - строка адреса

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, decode_responses=True)

    def get(self, phone: PhoneNumber):
        key = str(phone)
        data = super().get(key)
        if data is not None:
            return CustomerAddr(phone=phone, address=data)
        raise False

    def create(self, customer_addr: CustomerAddr) -> bool:
        key = str(customer_addr.phone)
        if super().set(key, customer_addr.address.encode('UTF-8'), nx=True):
            return True
        return False

    def update(self, customer_addr: CustomerAddr) -> bool:
        key = str(customer_addr.phone)
        if super().set(key, customer_addr.address.encode('UTF-8'), xx=True):
            return True
        return False

    def delete(self, phone: PhoneNumber) -> bool:
        key = str(phone)
        try:
            return super().delete(key) > 0
        except Exception:
            return False


redis_client = RedisWrapper(host=REDIS_HOST, username=REDIS_USERNAME,
                            port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB)


@app.get(ENDPOINT_PREFIX, response_model=CustomerAddr,
         description="Возвращает адрес клиента по телефонному номеру.",
         responses={404: {}, })
async def get_address_by_phone(phone: PhoneNumber) -> CustomerAddr:
    result = redis_client.get(phone)
    if result is not None:
        return CustomerAddr(phone=phone, address=result["address"])
    raise HTTPException(status_code=404, detail="Phone number not found.")


@app.post(ENDPOINT_PREFIX, response_model=SystemResponse, status_code=201,
          description="Создать запись адреса для для телефонного номера.",
          responses={409: {}, })
async def create_address_by_phone(data: CustomerAddr, response: Response) -> SystemResponse:
    result = redis_client.create(data)
    if result:
        return SystemResponse(detail="Created", customer_addr=data)
    else:
        response.status_code = 409
        return SystemResponse(detail="conflict: phone already exists", customer_addr=data)


@app.put(ENDPOINT_PREFIX, response_model=SystemResponse,
         description="Обновить адрес для указанного телефонного номера.",
         responses={404: {}, })
async def update_address_by_phone(data: CustomerAddr, response: Response) -> SystemResponse:
    result = redis_client.update(data, )
    if result:
        return SystemResponse(detail="Updated", customer_addr=data)

    response.status_code = 404
    return SystemResponse(detail="Phone not found", customer_addr=data)


@app.delete(ENDPOINT_PREFIX, status_code=204,
            description="Удалить запись адреса для телефонного номера.",
            responses={404: {}, })
async def delete_address_by_phone(phone: PhoneNumber):
    result = redis_client.delete(phone)
    if result:
        return
    raise HTTPException(status_code=404, detail="Phone number not found.")
