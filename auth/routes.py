from flask import Blueprint, request, jsonify
import pytz
from database import db, Client, FitnessClass, Session, Booking

auth_bp = Blueprint("auth", __name__)

# -------------------------------
# List available classes
# -------------------------------


@auth_bp.route("/classes", methods=["GET"])
def list_classes():
    timezone = request.args.get("timezone", "Asia/Kolkata")  # default to IST
    classes = FitnessClass.query.all()
    result = []
    try:
        for fitness_class in classes:
            for session in fitness_class.sessions:
                result.append({
                    "id": fitness_class.id,
                    "class": fitness_class.name,
                    "description": fitness_class.description,
                    "start_time": session.start_time_local(timezone).strftime("%Y-%m-%d %H:%M"),
                    "end_time": session.end_time_local(timezone).strftime("%Y-%m-%d %H:%M"),
                    "capacity": session.capacity,
                    "spots_left": session.spots_left()
                })
    except pytz.UnknownTimeZoneError:
        return jsonify({"error": f"Invalid timezone: {timezone}"}), 400
    return jsonify(result)

# -------------------------------
# Book a session
# -------------------------------


@auth_bp.route("/book", methods=["POST"])
def book_session():
    data = request.get_json()
    client_name = data.get("client_name")
    client_email = data.get("client_email")
    session_id = data.get("session_id")

    if not (client_name and client_email and session_id):
        return jsonify({"error": "client_name and client_email and session_id required"}), 400

    session = Session.query.get(session_id)
    if not session or session.spots_left() <= 0:
        return jsonify({"message": "Booking failed – session full or already booked"}), 400
    client = Client.query.filter_by(email=client_email).first()
    booking = Booking(client_id=client.id, session_id=session_id)
    try:
        db.session.add(booking)
        db.session.commit()
        success = True
    except Exception:
        db.session.rollback()
        success = False
    finally:
        if success:
            return jsonify({"message": "Booking successful"}), 200
        else:
            return jsonify({"message": "Booking failed – session full or already booked"}), 400

# -------------------------------
# Get all bookings for a client by email
# -------------------------------


@auth_bp.route("/bookings", methods=["GET"])
def get_bookings():
    email = request.args.get("email")
    timezone = request.args.get("timezone", "Asia/Kolkata")  # default to IST

    if not email:
        return jsonify({"error": "email query parameter is required"}), 400

    client = Client.query.filter_by(email=email).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404

    result = []
    try:
        for booking in client.bookings:
            session = booking.session
            result.append({
                "session_id": session.id,
                "class": session.fitness_class.name,
                "start_time": session.start_time_local(timezone).strftime("%Y-%m-%d %H:%M"),
                "end_time": session.end_time_local(timezone).strftime("%Y-%m-%d %H:%M")
            })
    except pytz.UnknownTimeZoneError:
        return jsonify({"error": f"Invalid timezone: {timezone}"}), 400

    return jsonify({
        "client": client.name,
        "email": client.email,
        "bookings": result
    })
