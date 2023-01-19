import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from project.models import (
    User,
    Role,
    Location,
    Trip,
    TripStatus,
    RequestStatus,
    TripPassenger
)

from project import db, bcrypt
from project.exceptions import APIError
from project.api.authentications import authenticate
from project.api.validators import field_type_validator, required_validator

logger = logging.getLogger(__name__)

trip_blueprint = Blueprint('trip', __name__, template_folder='templates')


@trip_blueprint.route('/trip/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong!'
    })


@trip_blueprint.route('/trip/list', methods=['GET'])
def get_trips():
    """Get all trips"""
    trips = Trip.query.all()
    response_object = {
        'status': True,
        'data': {
            'trips': [trip.to_json() for trip in trips]
        }
    }
    return jsonify(response_object), 200


@trip_blueprint.route('/trip/get', methods=['GET'])
@authenticate
def get_user_trips(user_id):
    """Get all trips for a user"""
    trips = Trip.query.filter_by(driver_id=user_id).all()
    response_object = {
        'status': True,
        'data': {
            'trips': [trip.to_json() for trip in trips]
        }
    }
    return jsonify(response_object), 200


@trip_blueprint.route('/trip/get/<int:trip_id>', methods=['GET'])
@authenticate
def get_trip_by_id(user_id, trip_id):
    """Get a single trip"""
    trip = Trip.query.filter_by(id=trip_id, driver_id=user_id).first()
    if not trip:
        response_object = {
            'status': False,
            'message': 'Trip does not exist',
        }
        return jsonify(response_object), 200

    passengers = TripPassenger.query.filter_by(
        trip_id=trip_id, request_status=RequestStatus.accepted).all()

    response_object = {
        'status': True,
        'data': {
            'trip': trip.to_json(),
            'passengers': [passenger.to_json() for passenger in passengers]
        }
    }
    return jsonify(response_object), 200


@trip_blueprint.route('/trip/create', methods=['POST'])
@authenticate
def create_trip(user_id):
    """Create a new trip"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can create trips'
            return jsonify(response_object), 200

        post_data = request.get_json()
        if not post_data:
            return jsonify(response_object), 200

        field_types = {
            "origin": dict, "destination_id": int, "date": str,
            "time": str, "number_of_seats": int, "carpool": bool
        }

        required_fields = list(field_types.keys())
        required_fields.remove('carpool')

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        source = post_data.get('origin')
        destination_id = post_data.get('destination_id')
        date = post_data.get('date')
        time = post_data.get('time')
        number_of_seats = post_data.get('number_of_seats')
        carpool = post_data.get('carpool') or False

        # Validate date and time
        if datetime.strptime(date + ' ' + time, '%Y-%m-%d %H:%M:%S') < datetime.now():
            response_object['message'] = 'Trip cannot be in the past, ' \
                'please check the date and time'
            return jsonify(response_object), 200

        if number_of_seats < 1:
            response_object['message'] = 'Number of seats must be greater than 0'
            return jsonify(response_object), 200

        trip = Trip.query.filter_by(driver_id=user_id, date=date).first()
        if trip and trip.status in [TripStatus.active, TripStatus.pending]:
            status = "an active" if trip.status == TripStatus.active \
                else "a pending"

            response_object['message'] = "Sorry, there's {} trip for you " \
                                         "on this date.".format(status)
            return jsonify(response_object), 200

        field_types = {
            "latitude": float, "longitude": float, "place": str
        }

        required_fields = list(field_types.keys())
        required_fields.remove("place")

        source = field_type_validator(source, field_types)
        required_validator(source, required_fields)

        source = Location(
            latitude=source.get("latitude"),
            longitude=source.get("longitude"),
            place=source.get("place")
        )

        source.insert()

        destination = Location.query.get(destination_id)
        if not destination:
            response_object['message'] = 'Destination does not exist'
            return jsonify(response_object), 200

        trip = Trip(
            driver_id=user_id,
            source_id=source.id,
            destination_id=destination_id,
            date=date,
            time=time,
            number_of_seats=number_of_seats,
            carpool=carpool
        )

        trip.insert()

        response_object['status'] = True
        response_object['message'] = 'Trip created successfully'
        response_object['data'] = {
            'trip': trip.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@trip_blueprint.route('/trip/update/<int:trip_id>', methods=['PATCH'])
@authenticate
def update_trip(user_id, trip_id):
    """Update a trip"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can update trips'
            return jsonify(response_object), 200

        trip = Trip.query.filter_by(id=trip_id, driver_id=user_id).first()
        if not trip:
            response_object['message'] = 'Trip does not exist'
            return jsonify(response_object), 200

        post_data = request.get_json()
        if not post_data:
            return jsonify(response_object), 200

        field_types = {
            "origin": dict, "destination_id": int, "date": str,
            "time": str, "number_of_seats": int, "carpool": bool
        }

        post_data = field_type_validator(post_data, field_types)

        source = post_data.get('origin')
        destination_id = post_data.get('destination_id')
        date = post_data.get('date')
        time = post_data.get('time')
        number_of_seats = post_data.get('number_of_seats')
        carpool = post_data.get('carpool')

        # Validate number of seats
        if number_of_seats:
            if number_of_seats < 1:
                response_object['message'] = 'Number of seats must be greater than 0'
                return jsonify(response_object), 200

        # Validate date and time
        if date or time:
            new_datetime = (date or trip.date) + ' ' + (time or trip.time)
            if (datetime.strptime(new_datetime, '%Y-%m-%d %H:%M:%S') < datetime.now()):
                response_object['message'] = 'Trip cannot be in the past, ' \
                    'please check the date'
                return jsonify(response_object), 200

            # check date conflict
            if date:
                trip_conflict = Trip.query.filter(
                    Trip.driver_id == user_id,
                    Trip.date == date,
                    Trip.id != trip_id
                ).first()

                if trip_conflict and trip_conflict.status in [TripStatus.active, TripStatus.pending]:
                    status = "an active" if trip_conflict.status == TripStatus.active \
                        else "a pending"

                    response_object['message'] = "Sorry, there's {} trip for you " \
                                                 "on this date.".format(status)
                    return jsonify(response_object), 200

        if destination_id:
            destination = Location.query.get(destination_id)
            if not destination:
                response_object['message'] = 'Destination does not exist'
                return jsonify(response_object), 200

        field_types = {
            "latitude": float, "longitude": float, "place": str
        }

        required_fields = list(field_types.keys())
        required_fields.remove("place")

        source = field_type_validator(source, field_types)
        required_validator(source, required_fields)

        old_source = Location.query.get(trip.source_id)
        if old_source:
            old_source.latitude = source.get("latitude") or old_source.latitude
            old_source.longitude = source.get(
                "longitude") or old_source.longitude
            old_source.place = source.get("place") or old_source.place

            old_source.update()

        else:
            old_source = Location(
                latitude=source.get("latitude"),
                longitude=source.get("longitude"),
                place=source.get("place")
            )

            old_source.insert()

        trip.source_id = old_source.id or trip.source_id
        trip.destination_id = destination_id or trip.destination_id
        trip.date = date or trip.date
        trip.time = time or trip.time
        trip.number_of_seats = number_of_seats or trip.number_of_seats
        trip.carpool = carpool if carpool is not None else trip.carpool

        trip.update()

        response_object['status'] = True
        response_object['message'] = 'Trip updated successfully'
        response_object['data'] = {
            'trip': trip.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@trip_blueprint.route('/trip/delete/<int:trip_id>', methods=['DELETE'])
@authenticate
def delete_trip(user_id, trip_id):
    """Delete a trip"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can delete trips'
            return jsonify(response_object), 200

        trip = Trip.query.filter_by(id=trip_id, driver_id=user_id).first()
        if not trip:
            response_object['message'] = 'Trip does not exist'
            return jsonify(response_object), 200

        TripPassenger.query.filter_by(trip_id=trip_id).delete()

        trip.delete()

        response_object['status'] = True
        response_object['message'] = 'Trip deleted successfully'

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@trip_blueprint.route('/trip/status/<int:trip_id>', methods=['GET', 'PUT'])
@authenticate
def trip_status(user_id, trip_id):
    """Update a trip status"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can access trip status'
            return jsonify(response_object), 200

        trip = Trip.query.filter_by(id=trip_id, driver_id=user_id).first()
        if not trip:
            response_object['message'] = 'Trip does not exist'
            return jsonify(response_object), 200

        if request.method == 'GET':
            response_object['status'] = True
            response_object['message'] = 'Trip status retrieved successfully'
            response_object['data'] = {
                'status': trip.status.name
            }

            return jsonify(response_object), 200

        post_data = request.get_json()
        if not post_data:
            return jsonify(response_object), 200

        field_types = {"status": str}
        required_fields = ["status"]

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        status = str(post_data.get('status')).lower()

        if status not in TripStatus.__members__:
            response_object['message'] = 'Invalid trip status'
            return jsonify(response_object), 200

        if TripStatus[status].value < trip.status.value and trip.status != TripStatus.active:
            response_object['message'] = 'Trip status cannot be reverted from {} to {}'.format(
                trip.status.name, status)
            return jsonify(response_object), 200

        trip.status = TripStatus[status]
        trip.update()

        response_object['status'] = True
        response_object['message'] = 'Trip status updated successfully'
        response_object['data'] = {
            'status': trip.status.name
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@trip_blueprint.route('/trip/status', methods=['GET'])
@authenticate
def trip_status_list(user_id):
    """Get trip status list"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can access trips'
            return jsonify(response_object), 200

        status = str(request.args.get('status')).lower()
        if status and status not in TripStatus.__members__:
            response_object['message'] = 'Invalid trip status'
            return jsonify(response_object), 200

        trips = Trip.query.filter_by(driver_id=user_id)
        if status:
            trips = trips.filter_by(status=TripStatus[status])

        trips = trips.order_by(Trip.date.desc()).all()

        trips = [trip.to_json() for trip in trips]

        for trip in trips:
            passengers = TripPassenger.query.filter_by(
                trip_id=trip['id']).all()
            trip['number_of_passengers'] = len(passengers)

        response_object['status'] = True
        response_object['message'] = '{} trips retrieved successfully'.format(
            str(status).capitalize() if status else 'All')
        response_object['data'] = {
            'trips': trips
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@trip_blueprint.route('/trip/requests', methods=['GET'])
@authenticate
def trip_requests(user_id):
    """Get all trip requests"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can access trip requests'
            return jsonify(response_object), 200

        pending_requests = TripPassenger.query.join(
            Trip, Trip.id == TripPassenger.trip_id
        ).filter(
            Trip.driver_id == user_id,
            Trip.status == TripStatus.pending,
            TripPassenger.request_status == RequestStatus.pending
        ).order_by(
            TripPassenger.timestamp.desc()
        ).all()

        response_object['status'] = True
        response_object['message'] = '{} trip request(s) available'.format(
            len(pending_requests))
        response_object['data'] = {
            'requests': [request.to_json() for request in pending_requests]
        }

        return jsonify(response_object), 200

    except Exception as e:
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@trip_blueprint.route('/trip/request/<int:request_id>', methods=['GET', 'PUT'])
@authenticate
def trip_request(user_id, request_id):
    """Get a trip request"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        driver = User.query.get(user_id)
        if driver.role != Role.driver:
            response_object['message'] = 'Only drivers can access trip requests'
            return jsonify(response_object), 200

        passenger_request = TripPassenger.query.filter(
            TripPassenger.id == request_id,
            TripPassenger.request_status == RequestStatus.pending
        ).first()
        if not passenger_request:
            response_object['message'] = 'Trip request does not exist'
            return jsonify(response_object), 200

        if request.method == 'GET':
            response_object['status'] = True
            response_object['message'] = 'Trip request retrieved successfully'
            response_object['data'] = {
                'request': passenger_request.to_json()
            }

            return jsonify(response_object), 200

        post_data = request.get_json()
        if not post_data:
            return jsonify(response_object), 200

        field_types = {"status": str}
        required_fields = ["status"]

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        status = str(post_data.get('status')).lower()

        if status not in RequestStatus.__members__:
            response_object['message'] = 'Invalid request status'
            return jsonify(response_object), 200

        if RequestStatus[status].value < passenger_request.request_status.value:
            response_object['message'] = 'Request status cannot be reverted from {} to {}'.format(
                request.request_status.name, status)
            return jsonify(response_object), 200

        passenger_request.request_status = RequestStatus[status]
        passenger_request.update()

        response_object['status'] = True
        response_object['message'] = 'Trip request updated successfully'
        response_object['data'] = {
            'request': passenger_request.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        response_object['message'] = str(e)
        return jsonify(response_object), 200
