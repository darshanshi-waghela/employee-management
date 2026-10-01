import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        yield client


def login(client):
    client.post("/register", json={"username": "admin", "password": "pass123"})
    return client.post("/login", json={"username": "admin", "password": "pass123"})


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_register_and_login(client):
    r = login(client)
    assert r.status_code == 200


def test_wrong_password(client):
    client.post("/register", json={"username": "admin", "password": "pass123"})
    r = client.post("/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_employees_require_login(client):
    r = client.get("/employees")
    assert r.status_code == 401


def test_crud_employee(client):
    login(client)

    # Create
    r = client.post("/employees", json={"name": "Asha", "email": "asha@test.com", "department": "IT", "position": "Dev"})
    assert r.status_code == 201
    emp_id = r.get_json()["id"]

    # Read
    r = client.get(f"/employees/{emp_id}")
    assert r.status_code == 200
    assert r.get_json()["name"] == "Asha"

    # Update
    r = client.put(f"/employees/{emp_id}", json={"position": "Senior Dev"})
    assert r.status_code == 200
    assert r.get_json()["position"] == "Senior Dev"

    # List
    r = client.get("/employees")
    assert len(r.get_json()) == 1

    # Delete
    r = client.delete(f"/employees/{emp_id}")
    assert r.status_code == 200
    assert client.get(f"/employees/{emp_id}").status_code == 404