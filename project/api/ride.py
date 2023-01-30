import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from project.models import (
    User,
    Location,
    Trip,
    TripStatus,
    RequestStatus,
    TripPassenger,
    Rating
)

from project import db
from project.api.authentications import authenticate
from project.api.validators import field_type_validator, required_validator

logger = logging.getLogger(__name__)

ride_blueprint = Blueprint("ride", __name__, template_folder="templates")


@ride_blueprint.route("/ride/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "success",
        "message": "pong!"
    })


@ride_blueprint.route("/ride/list", methods=["GET"])
def list_rides():
    """List all rides"""
    rides = TripPassenger.query.all()
    return jsonify({
        "status": True,
        "message": "Rides retrieved successfully",
        "data": {
            "rides": [ride.to_json() for ride in rides]
        }
    })


@ride_blueprint.route("/ride/get", methods=["GET"])
@authenticate
def get(user_id):
    """Get available rides for a user sorted by driver rating"""
    user = User.query.get(user_id)

    rides = Trip.query.filter(
        Trip.status == TripStatus.pending,
        Trip.number_of_seats > 0,
    ).order_by(
        Trip.date.asc(),
        Trip.time.asc()
    ).all()

    rides_json = []
    for ride in rides:
        user_trip = TripPassenger.query.filter_by(
            trip_id=ride.id,
            passenger_id=user_id,
        ).all()

        ride_requested = False
        for trip in user_trip:
            if trip.request_status in [RequestStatus.pending, RequestStatus.accepted]:
                ride_requested = True
                break

        if not ride_requested:
            ride_json = ride.to_json()
            ride_json["avg_rating"] = Rating.get_average_rating(
                ride.driver_id)
            rides_json.append(ride_json)

    return jsonify({
        "status": True,
        "message": "{} ride(s) available for {}".format(len(rides_json), user.fullname),
        "data": {
            "trips": rides_json
        }
    })


@ride_blueprint.route("/ride/get/<int:ride_id>", methods=["GET"])
@authenticate
def get_ride(user_id, ride_id):
    """Get a ride"""
    trip = Trip.query.filter_by(
        id=ride_id
    ).first()
    if not trip:
        return jsonify({
            "status": False,
            "message": "Trip not found"
        }), 200

    ride = TripPassenger.query.filter_by(
        trip_id=ride_id,
        passenger_id=user_id,
        request_status=RequestStatus.accepted
    ).first()
    if not ride:
        return jsonify({
            "status": False,
            "message": "Ride not found"
        }), 200

    ride = ride.to_json()
    ride["trip"] = trip.to_json()

    return jsonify({
        "status": True,
        "message": "Ride retrieved successfully",
        "data": {
            "ride": ride
        }
    })


@ride_blueprint.route("/ride/create", methods=["POST"])
@authenticate
def create(user_id):
    """Create a ride"""
    response_object = {
        "status": False,
        "message": "Invalid payload."
    }

    try:
        data = request.get_json()
        if not data:
            return jsonify(response_object), 200

        field_types = {
            "trip_id": int, "origin": dict, "seats_booked": int
        }

        required_fields = list(field_types.keys())

        post_data = field_type_validator(data, field_types)
        required_validator(post_data, required_fields)

        trip_id = post_data.get("trip_id")
        source = post_data.get("origin")
        seats_booked = post_data.get("seats_booked")

        trip = Trip.query.filter_by(id=trip_id).first()
        if not trip:
            return jsonify({
                "status": False,
                "message": "Ride not found"
            }), 200

        if trip.status != TripStatus.pending:
            return jsonify({
                "status": False,
                "message": "You can't book {} ride".format(trip.status.name)
            }), 200

        if trip.driver_id == user_id:
            return jsonify({
                "status": False,
                "message": "You cannot book a ride you created"
            }), 200

        if seats_booked > trip.number_of_seats:
            return jsonify({
                "status": False,
                "message": "Not enough seats available"
            }), 200

        ride = TripPassenger.query.filter_by(
            trip_id=trip_id,
            passenger_id=user_id
        ).first()

        if ride and ride.request_status not in [RequestStatus.rejected, RequestStatus.cancelled]:
            return jsonify({
                "status": False,
                "message": "You have already booked this ride"
            }), 200

        field_types = {
            "latitude": float, "longitude": float, "place": str
        }

        required_fields = list(field_types.keys())

        source = field_type_validator(source, field_types)
        required_validator(source, required_fields)

        source = Location(
            latitude=source.get("latitude"),
            longitude=source.get("longitude"),
            place=source.get("place")
        )

        source.insert()

        ride = TripPassenger(
            trip_id=trip_id,
            passenger_id=user_id,
            source_id=source.id,
            destination_id=trip.destination_id,
            seats_booked=seats_booked
        )

        ride.insert()

        response_object["status"] = True
        response_object["message"] = "Ride booked successfully"
        response_object["data"] = {
            "ride": ride.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object["message"] = str(e)
        return jsonify(response_object), 200


@ride_blueprint.route("/ride/update/<int:ride_id>", methods=["PATCH", "PUT"])
@authenticate
def update(user_id, ride_id):
    """Update a ride"""
    response_object = {
        "status": False,
        "message": "Invalid payload."
    }

    try:
        data = request.get_json()
        if not data:
            return jsonify(response_object), 200

        trip = Trip.query.filter_by(
            id=ride_id
        ).first()
        if not trip:
            return jsonify({
                "status": False,
                "message": "Trip not found"
            }), 200

        ride = TripPassenger.query.filter_by(
            trip_id=ride_id,
            passenger_id=user_id
        ).first()

        if not ride:
            return jsonify({
                "status": False,
                "message": "Ride not found"
            }), 200

        if ride.request_status != RequestStatus.pending:
            return jsonify({
                "status": False,
                "message": "You can't update {} ride".format(ride.request_status.name)
            }), 200

        field_types = {
            "origin": dict, "seats_booked": int
        }

        required_fields = list(field_types.keys())

        post_data = field_type_validator(data, field_types)
        required_validator(post_data, required_fields)

        source = post_data.get("origin")
        seats_booked = post_data.get("seats_booked")

        if trip.status != TripStatus.pending:
            return jsonify({
                "status": False,
                "message": "You can't update {} ride".format(trip.status.name)
            }), 200

        if trip.number_of_seats < (seats_booked - ride.seats_booked):
            return jsonify({
                "status": False,
                "message": "Not enough seats available"
            }), 200

        field_types = {
            "latitude": float, "longitude": float, "place": str
        }

        required_fields = list(field_types.keys())

        source = field_type_validator(source, field_types)

        location = Location.query.get(ride.source_id)

        location.latitude = source.get("latitude") or location.latitude
        location.longitude = source.get("longitude") or location.longitude
        location.place = source.get("place") or location.place

        location.update()

        ride.seats_booked = seats_booked
        ride.update()

        response_object["status"] = True
        response_object["message"] = "Ride updated successfully"
        response_object["data"] = {
            "ride": ride.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object["message"] = str(e)
        return jsonify(response_object), 200


@ride_blueprint.route("/ride/delete/<int:ride_id>", methods=["DELETE"])
@authenticate
def delete(user_id, ride_id):
    """Delete a ride"""
    response_object = {
        "status": False,
        "message": "Invalid payload."
    }

    try:
        ride = TripPassenger.query.filter_by(
            trip_id=ride_id,
            passenger_id=user_id
        ).first()

        if not ride:
            return jsonify({
                "status": False,
                "message": "Ride not found"
            }), 200

        if ride.request_status != RequestStatus.accepted:
            return jsonify({
                "status": False,
                "message": "You can't delete {} ride".format(ride.request_status.name)
            }), 200

        location = Location.query.filter_by(
            id=ride.source_id
        ).first()

        ride.delete()
        location.delete()

        response_object["status"] = True
        response_object["message"] = "Ride deleted successfully"

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object["message"] = str(e)
        return jsonify(response_object), 200


@ride_blueprint.route("/ride/status", methods=["GET"])
@authenticate
def ride_status(user_id):
    """Get ride status"""
    response_object = {
        "status": False,
        "message": "Invalid payload."
    }

    try:
        status = request.args.get("status")
        status = str(status).lower() if status else None

        if status and status not in TripStatus.__members__:
            response_object["message"] = "Invalid status: {}".format(status)
            return jsonify(response_object), 200

        rides = Trip.query.join(
            TripPassenger, TripPassenger.trip_id == Trip.id
        ).filter(
            TripPassenger.passenger_id == user_id,
            TripPassenger.request_status == RequestStatus.accepted,
        )

        if status:
            rides = rides.filter(Trip.status == TripStatus[status])

        rides = rides.order_by(
            Trip.date.asc(),
            Trip.time.asc()
        ).all()

        response_object["status"] = True
        response_object["message"] = "{} ride(s) found".format(len(rides))
        response_object["data"] = {
            "rides": [ride.to_json() for ride in rides]
        }

        return jsonify(response_object), 200

    except Exception as e:
        logger.error(e)
        response_object["message"] = str(e)
        return jsonify(response_object), 200


@ride_blueprint.route("/ride/feedback/<int:ride_id>", methods=["POST"])
@authenticate
def rate_ride(user_id, ride_id):
    """Rate a ride"""
    response_object = {
        "status": False,
        "message": "Invalid payload."
    }

    try:
        post_data = request.get_json()
        if not post_data:
            return jsonify(response_object), 200

        field_types = {
            "rating": int, "comment": str
        }

        required_fields = list(field_types.keys())
        required_fields.remove("comment")

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        rating = post_data.get("rating")
        feedback = post_data.get("comment")

        if rating < 1 or rating > 5:
            return jsonify({
                "status": False,
                "message": "Rating must be between 1 and 5"
            }), 200

        trip = Trip.query.join(
            TripPassenger, Trip.id == TripPassenger.trip_id
        ).filter(
            TripPassenger.passenger_id == user_id,
            TripPassenger.request_status == RequestStatus.accepted,
            Trip.id == ride_id
        ).first()

        if not trip:
            return jsonify({
                "status": False,
                "message": "Trip not found"
            }), 200

        if trip.status != TripStatus.completed:
            return jsonify({
                "status": False,
                "message": "You can't rate {} trip".format(trip.status.name)
            }), 200

        curr_rating = Rating.query.filter_by(
            trip_id=trip.id,
            passenger_id=user_id,
            driver_id=trip.driver_id
        ).first()

        if curr_rating:
            return jsonify({
                "status": False,
                "message": "You have already rated this trip"
            }), 200

        rating = Rating(
            passenger_id=user_id,
            driver_id=trip.driver_id,
            trip_id=trip.id,
            rating=rating
        )

        rating.insert()

        if feedback:
            rating.feedback = str(feedback).strip().capitalize()
            rating.update()

        response_object["status"] = True
        response_object["message"] = "Trip rated successfully"
        response_object["data"] = {
            "rating": rating.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object["message"] = str(e)
        return jsonify(response_object), 200
