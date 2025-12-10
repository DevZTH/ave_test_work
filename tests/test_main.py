
def _payload(phone: str, address: str) -> dict:
    return {"phone": phone, "address": address}

def test_create_and_get_address_success(client):
    phone = "+447911123456"
    address = "г. Белгород, ул. Щорса, 123"
    r = client.post("/addr_by_phone", json=_payload(phone, address))
    assert r.status_code == 201
    body = r.json()
    assert body["detail"] == "Created"

    # un RFC3966
    def norm(p: str) -> str:
        s = p.replace('tel:', '')
        return '+' + ''.join(ch for ch in s if ch.isdigit())

    assert norm(body["customer_addr"]["phone"]) == norm(phone)

    r2 = client.get("/addr_by_phone", params={"phone": phone})
    assert r2.status_code == 200
    assert r2.json()["address"] == address


def test_create_conflict_existing(client):
    phone = "+447911123457"
    address = "Some address 1"
    r1 = client.post("/addr_by_phone", json=_payload(phone, address))
    assert r1.status_code == 201
    r2 = client.post("/addr_by_phone", json=_payload(phone, address))
    # conflict
    assert r2.status_code == 409


def test_update_success_and_get(client):
    phone = "+447911123458"
    address = "Original address"
    new_address = "Updated address"
    client.post("/addr_by_phone", json=_payload(phone, address))
    r = client.put("/addr_by_phone", json=_payload(phone, new_address))
    assert r.status_code == 200
    assert r.json()["detail"] == "Updated"

    r2 = client.get("/addr_by_phone", params={"phone": phone})
    assert r2.status_code == 200
    assert r2.json()["address"] == new_address


def test_update_not_found(client):
    phone = "+447911123459"
    r = client.put("/addr_by_phone", json=_payload(phone, "No such address"))
    assert r.status_code == 404


def test_delete_success_and_get_not_found(client):
    phone = "+447911123460"
    address = "To be deleted"
    client.post("/addr_by_phone", json=_payload(phone, address))
    r = client.delete("/addr_by_phone", params={"phone": phone})
    assert r.status_code == 204

    r2 = client.get("/addr_by_phone", params={"phone": phone})
    assert r2.status_code == 404


def test_delete_not_found(client):
    r = client.delete("/addr_by_phone", params={"phone": "+79772223344"})
    assert r.status_code == 404


def test_phone_validation_errors(client):
    r = client.post("/addr_by_phone", json=_payload("14155552671", "a" * 20))
    assert r.status_code == 422

    r2 = client.post("/addr_by_phone", json=_payload("+1ABC5552671", "a" * 20))
    assert r2.status_code == 422


def test_multi_country_phone_numbers(client):
    """Positive cases: store and retrieve phones from several countries."""
    samples = [
        ("+447911123460", "UK address sample"),    # UK
        ("+141 55552671", "US address sample"),    # US
        ("+7-911-123-45-67", "RU address sample"),    # Russia
        ("+9-19876543210", "IN address sample"),   # India
        ("+8 190 123 45678", "JP address sample"),   # Japan
    ]

    for phone, addr in samples:
        r = client.post("/addr_by_phone", json=_payload(phone, addr))
        assert r.status_code == 201, f"create failed for {phone}"
        # get and verify
        r2 = client.get("/addr_by_phone", params={"phone": phone})
        assert r2.status_code == 200, f"get failed for {phone}"
        assert r2.json()["address"] == addr
