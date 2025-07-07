# tests/test_api.py
from datetime import datetime, timedelta
import pytest
import pytz
from sqlalchemy.pool import StaticPool

from app import app as flask_app
from database import db, seed_all, Client, FitnessClass, create_session


# ------------------------------------------------------------------
# Single helper to create a fresh client & session inside ONE context
# ------------------------------------------------------------------
def make_demo_data():
    """Return (client_id, session_id) created in current app‑context."""
    # unique email so we never collide with seed data
    now = datetime.utcnow()
    timestamp = f"{int(now.timestamp())}{now.microsecond}"
    email = f"test{timestamp}@example.com"

    client = Client(name="Bob", email=email)
    db.session.add(client)
    db.session.commit()

    # Tomorrow 07‑08 IST, capacity 1 (good for double‑booking test)
    ist = pytz.timezone("Asia/Kolkata")
    tomorrow = datetime.now(ist).date() + timedelta(days=1)

    start_ist = f"{tomorrow} 07:00"
    end_ist   = f"{tomorrow} 08:00"

    yoga_cls = FitnessClass.query.filter_by(name="Yoga").first()
    sess = create_session(
        class_id=yoga_cls.id,
        start_ist=start_ist,
        end_ist=end_ist,
        capacity=3,
    )

    return "Bob", sess.id, email


# ------------------------------------------------------------------
# Pytest fixture – shared in‑memory DB, one app‑context per test
# ------------------------------------------------------------------
@pytest.fixture(scope="function")
def client():
    # In‑memory DB that survives across all connections
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    flask_app.config["TESTING"] = True

    with flask_app.app_context():
        db.create_all()
        seed_all()                     # Yoga / Zumba / HIIT + sample data
        testing_client = flask_app.test_client()
        yield testing_client           # ——— tests run here ———
        db.session.remove()
        db.drop_all()


# ------------------------------------------------------------------
# 1) /classes lists Yoga
# ------------------------------------------------------------------
def test_list_classes(client):
    rv = client.get("/classes")
    assert rv.status_code == 200
    assert any(item["class"] == "Yoga" for item in rv.get_json())


# ------------------------------------------------------------------
# 2) Booking workflow
# ------------------------------------------------------------------
def test_booking_workflow(client):
    with flask_app.app_context():
        cid, sid, email = make_demo_data()

    # Book
    response = client.post("/book", json={"client_name": cid, "client_email": email, "session_id": sid})
    print(response.status_code)
    print(response.get_json())  # or response.data.decode() if not JSON
    assert response.status_code == 200

    # Retrieve in UTC
    rv = client.get(f"/bookings?email={email}&timezone=UTC")
    data = rv.get_json()
    assert rv.status_code == 200
    assert len(data["bookings"]) == 1
    assert data["bookings"][0]["session_id"] == sid


# ------------------------------------------------------------------
# 3) Double‑booking rejected
# ------------------------------------------------------------------
def test_double_booking_rejected(client):
    with flask_app.app_context():
        cid, sid, email = make_demo_data()

    # first booking OK
    response = client.post("/book", json={"client_name": cid, "client_email": email, "session_id": sid})
    print(response.status_code)
    print(response.get_json())  # or response.data.decode() if not JSON
    assert response.status_code == 200

    # second booking should fail (capacity = 1)
    response = client.post("/book", json={"client_name": cid, "client_email": email, "session_id": sid})
    print(response.status_code)
    print(response.get_json())  # or response.data.decode() if not JSON
    assert response.status_code == 400
