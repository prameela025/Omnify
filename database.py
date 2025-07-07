from datetime import datetime, timedelta
import pytz
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# ------------------------------------------------------------------
# Configure Flask + SQLAlchemy
# ------------------------------------------------------------------
db = SQLAlchemy()


def init_db(app: Flask, db_path: str = "sqlite:///database.db") -> None:
    """Attach SQLAlchemy to the Flask app and create tables."""
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_all()

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)

    bookings = db.relationship("Booking", backref="client", lazy=True)

    def __repr__(self) -> str:
        return f"<Client {self.id} {self.name}>"


class FitnessClass(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.Text)

    sessions = db.relationship("Session", backref="fitness_class", lazy=True)

    def __repr__(self) -> str:
        return f"<Class {self.name}>"


class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    start_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    bookings = db.relationship("Booking", backref="session", lazy=True)

    # ------------ Convenience helpers -----------------------------

    @property
    def booked_count(self) -> int:
        return len(self.bookings)

    def spots_left(self) -> int:
        return self.capacity - self.booked_count

    # Convert UTC to any tz when needed
    def start_time_local(self, tz_name: str = "Asia/Kolkata") -> datetime:
        return self.start_time_utc.astimezone(pytz.timezone(tz_name))

    def end_time_local(self, tz_name: str = "Asia/Kolkata") -> datetime:
        return self.end_time_utc.astimezone(pytz.timezone(tz_name))

    def __repr__(self) -> str:
        return f"<Session {self.id} {self.start_time_utc.isoformat()}>"


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = (db.UniqueConstraint("client_id", "session_id", name="uq_client_session"),)

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)

    def __repr__(self) -> str:
        return f"<Booking c{self.client_id}-s{self.session_id}>"

# ------------------------------------------------------------------
# Seeding helpers
# ------------------------------------------------------------------


def ist_str_to_utc(ist_str: str, fmt: str = "%Y-%m-%d %H:%M") -> datetime:
    """
    Convert an IST datetime‑string (e.g., "2025-07-09 07:00") to
    a timezone‑aware UTC datetime object.
    """
    ist_zone = pytz.timezone("Asia/Kolkata")
    local_dt = ist_zone.localize(datetime.strptime(ist_str, fmt))
    return local_dt.astimezone(pytz.UTC)


def create_session(*, class_id: int, start_ist: str, end_ist: str, capacity: int = 10):
    """
    Create a Session using IST start/end strings.
    Returns the new Session ORM object.
    """
    start_utc = ist_str_to_utc(start_ist)
    end_utc = ist_str_to_utc(end_ist)

    new_session = Session(
        class_id=class_id,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        capacity=capacity,
    )
    db.session.add(new_session)
    db.session.commit()
    return new_session


def insert_default_classes() -> None:
    """Insert Yoga, Zumba, HIIT (idempotent)."""
    defaults = ["Yoga", "Zumba", "HIIT"]
    for name in defaults:
        if not FitnessClass.query.filter_by(name=name).first():
            db.session.add(FitnessClass(name=name, description=f"{name} class"))
    db.session.commit()


def insert_sample_clients() -> None:
    """Create a couple of demo clients if they don’t exist."""
    samples = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob",   "email": "bob@example.com"},
    ]
    for c in samples:
        if not Client.query.filter_by(email=c["email"]).first():
            db.session.add(Client(**c))
    db.session.commit()


def insert_sample_sessions() -> None:
    """Create one or two sessions for each default class in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    tomorrow = datetime.now(ist).date() + timedelta(days=1)

    class_specs = {
        "Yoga":  ["07:00", "18:00"],
        "Zumba": ["08:00"],
        "HIIT":  ["09:30"],
    }

    for class_name, times in class_specs.items():
        cls = FitnessClass.query.filter_by(name=class_name).first()
        if not cls:
            continue

        for t in times:
            start_str = f"{tomorrow} {t}"           # e.g., "2025-07-09 07:00"
            end_hour, end_min = map(int, t.split(":"))
            end_time = (datetime.combine(tomorrow, datetime.min.time())
                        .replace(hour=end_hour, minute=end_min)
                        + timedelta(hours=1)).strftime("%H:%M")
            end_str = f"{tomorrow} {end_time}"

            # Check if a session at that start already exists
            utc_start = ist_str_to_utc(start_str)
            if not Session.query.filter_by(start_time_utc=utc_start).first():
                create_session(
                    class_id=cls.id,
                    start_ist=start_str,
                    end_ist=end_str,
                    capacity=10,
                )


def seed_all() -> None:
    """Run all seed helpers idempotently."""
    insert_default_classes()
    insert_sample_clients()
    insert_sample_sessions()
