import os
import logging

from flask import Blueprint, jsonify, request
from flask import current_app

from project.models import (
    User,
    Role,
    Gender,
    Vehicle,
    Licence,
    Location
)

from project import db, bcrypt
from project.exceptions import APIError
from project.api.authentications import authenticate
from project.api.validators import email_validator, field_type_validator, required_validator


driver_blueprint = Blueprint('driver', __name__, template_folder='templates')
logger = logging.getLogger(__name__)


@driver_blueprint.route('/drivers/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@driver_blueprint.route('/drivers/list', methods=['GET'])
def get_all_drivers():
    """Get all drivers"""
    drivers = User.query.filter_by(role=Role.driver).all()
    response_object = {
        'status': True,
        'message': '{} driver(s) found'.format(len(drivers)),
        'data': {
            'drivers': [driver.to_json() for driver in drivers]
        }
    }
    return jsonify(response_object), 200


@driver_blueprint.route('/drivers/get/<int:driver_id>', methods=['GET'])
def get_single_driver(driver_id):
    """Get single driver details"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        driver_json = driver.to_json()
        vehicle = Vehicle.query.filter_by(user_id=int(driver_id)).first()
        licence = Licence.query.filter_by(user_id=int(driver_id)).first()

        driver_json['vehicle'] = vehicle.to_json() if vehicle else None
        driver_json['licence'] = licence.to_json() if licence else None

        response_object['status'] = True
        response_object['message'] = 'Driver found'
        response_object['data'] = {
            'driver': driver_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@driver_blueprint.route('/drivers/get', methods=['GET'])
@authenticate
def get_driver(driver_id):
    """Get single driver details"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        driver_json = driver.to_json()
        vehicle = Vehicle.query.filter_by(user_id=int(driver_id)).first()
        licence = Licence.query.filter_by(user_id=int(driver_id)).first()

        driver_json['vehicle'] = vehicle.to_json() if vehicle else None
        driver_json['licence'] = licence.to_json() if licence else None

        response_object['status'] = True
        response_object['message'] = 'Driver found'
        response_object['data'] = {
            'driver': driver_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@driver_blueprint.route('/drivers/update_info', methods=['PATCH'])
@authenticate
def update_driver_info(driver_id):
    """Update driver info"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    post_data = request.get_json()
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        field_types = {
            "fullname": str, "email": str, "password": str,
            "mobile_no": str, "profile_picture": str, "dob": str,
            "gender": str, "address": str, "active": bool
        }

        post_data = field_type_validator(post_data, field_types)

        if post_data.get("email"):
            email_validator(post_data["email"])

        if post_data.get("password"):
            driver.password = bcrypt.generate_password_hash(
                post_data.get('password'), current_app.config.get(
                    'BCRYPT_LOG_ROUNDS')
            ).decode()

        gender = post_data.get('gender')
        gender = str(gender).lower() if gender else None
        if gender and gender not in Gender.__members__:
            response_object['message'] = "Invalid gender {}".format(gender)
            return jsonify(response_object), 200

        driver.fullname = post_data.get('fullname') or driver.fullname
        driver.email = post_data.get('email') or driver.email
        driver.mobile_no = post_data.get('mobile_no') or driver.mobile_no
        driver.profile_picture = post_data.get(
            'profile_picture') or driver.profile_picture
        driver.dob = post_data.get('dob') or driver.dob
        driver.gender = Gender[gender] if gender else driver.gender
        driver.address = post_data.get('address') or driver.address
        driver.active = post_data.get('active') if post_data.get(
            'active') is not None else driver.active

        driver.update()
        driver_json = driver.to_json()

        vehicle = Vehicle.query.filter_by(user_id=driver.id).first()
        licence = Licence.query.filter_by(user_id=driver.id).first()

        driver_json["vehicle"] = vehicle.to_json() if vehicle else None
        driver_json["licence"] = licence.to_json() if licence else None

        response_object['status'] = True
        response_object['message'] = 'Driver info updated successfully'
        response_object['data'] = {
            'driver': driver_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@driver_blueprint.route('/drivers/update_vehicle', methods=['PATCH'])
@authenticate
def update_driver_vehicle(driver_id):
    """Update driver vehicle"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    post_data = request.get_json()
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        field_types = {
            "vehicle_no": str, "vehicle_image": str, "vehicle_plate_image": str
        }

        post_data = field_type_validator(post_data, field_types)

        vehicle = Vehicle.query.filter_by(user_id=driver.id).first()
        if not vehicle:
            vehicle = Vehicle(
                user_id=driver.id,
                vehicle_no=post_data.get('vehicle_no'),
                vehicle_image=post_data.get('vehicle_image'),
                vehicle_plate_image=post_data.get('vehicle_plate_image')
            )

            vehicle.insert()

            driver.vehicle_verified = True
            driver.update()

        else:
            vehicle.vehicle_no = post_data.get(
                'vehicle_no') or vehicle.vehicle_no
            vehicle.vehicle_image = post_data.get(
                'vehicle_image') or vehicle.vehicle_image
            vehicle.vehicle_plate_image = post_data.get(
                'vehicle_plate_image') or vehicle.vehicle_plate_image
            vehicle.update()

        vehicle_json = vehicle.to_json()

        response_object['status'] = True
        response_object['message'] = "{0}'s vehicle updated successfully".format(
            driver.fullname)
        response_object['data'] = {
            'vehicle': vehicle_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@driver_blueprint.route('/drivers/update_licence', methods=['PATCH'])
@authenticate
def update_driver_licence(driver_id):
    """Update driver licence"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    post_data = request.get_json()
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        field_types = {
            "licence_no": str, "licence_image_front": str, "licence_image_back": str
        }

        post_data = field_type_validator(post_data, field_types)

        licence = Licence.query.filter_by(user_id=driver.id).first()
        if not licence:
            licence = Licence(
                user_id=driver.id,
                licence_no=post_data.get('licence_no'),
                licence_image_front=post_data.get('licence_image_front'),
                licence_image_back=post_data.get('licence_image_back')
            )

            licence.insert()

            driver.licence_verified = True
            driver.update()

        else:
            licence.licence_no = post_data.get(
                'licence_no') or licence.licence_no
            licence.licence_image_front = post_data.get(
                'licence_image_front') or licence.licence_image_front
            licence.licence_image_back = post_data.get(
                'licence_image_back') or licence.licence_image_back
            licence.update()

        licence_json = licence.to_json()

        response_object['status'] = True
        response_object['message'] = "{0}'s licence updated successfully".format(
            driver.fullname)
        response_object['data'] = {
            'licence': licence_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@driver_blueprint.route('/drivers/update_location', methods=['PATCH'])
@authenticate
def update_driver_location(driver_id):
    """Update driver location"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    post_data = request.get_json()
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        field_types = {
            "latitude": float, "longitude": float, "place": str
        }

        post_data = field_type_validator(post_data, field_types)

        location = Location.query.get(driver.location_id)
        if not location:
            location = Location(
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude'),
                place=post_data.get('place')
            )

            location.insert()

        else:
            location.latitude = post_data.get('latitude') or location.latitude
            location.longitude = post_data.get(
                'longitude') or location.longitude
            location.place = post_data.get('place') or location.place
            location.update()

        driver.location_id = location.id
        driver.update()

        location_json = location.to_json()

        response_object['status'] = True
        response_object['message'] = "{0}'s location updated successfully".format(
            driver.fullname)
        response_object['data'] = {
            'location': location_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@driver_blueprint.route('/drivers/delete', methods=['DELETE'])
@authenticate
def delete_driver(driver_id):
    """Delete driver"""
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    try:
        driver = User.query.filter_by(
            id=int(driver_id), role=Role.driver).first()
        if not driver:
            return jsonify(response_object), 200

        licence = Licence.query.filter_by(user_id=driver.id).first()
        if licence:
            licence.delete()

        vehicle = Vehicle.query.filter_by(user_id=driver.id).first()
        if vehicle:
            vehicle.delete()

        location = Location.query.get(driver.location_id)
        if location:
            location.delete()

        driver.delete()

        response_object['status'] = True
        response_object['message'] = "Driver's account deleted successfully"

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200
