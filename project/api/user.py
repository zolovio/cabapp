import os
import random
import logging

from flask import Blueprint, jsonify, request
from flask import current_app, session

from project.models import (
    User,
    Role,
    Gender,
    Location
)

from project import db, bcrypt
from project.exceptions import APIError
from project.api.utils import send_email
from project.api.authentications import authenticate
from project.api.validators import email_validator, field_type_validator, required_validator


user_blueprint = Blueprint('user', __name__, template_folder='templates')
logger = logging.getLogger(__name__)


@user_blueprint.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@user_blueprint.route('/users/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': True,
        'message': 'pong V0.1!'
    })


@user_blueprint.route('/users/list', methods=['GET'])
def get_all_users():
    """Get all users"""
    users = User.query.filter_by(role=Role.user).all()
    response_object = {
        'status': True,
        'message': '{} user(s) found'.format(len(users)),
        'data': {
            'users': [user.to_json() for user in users]
        }
    }
    return jsonify(response_object), 200


@user_blueprint.route('/users/get/<int:user_id>', methods=['GET'])
def get_single_user(user_id):
    """Get single user details"""
    response_object = {
        'status': False,
        'message': 'User does not exist',
    }

    user = User.query.filter_by(id=int(user_id), role=Role.user).first()

    if not user:
        return jsonify(response_object), 200

    response_object['status'] = True
    response_object['message'] = 'User details retrieved successfully'
    response_object['data'] = {
        'user': user.to_json()
    }

    return jsonify(response_object), 200


@user_blueprint.route('/users/get', methods=['GET'])
@authenticate
def get_user_by_auth_token(user_id):
    """Get single user details"""
    response_object = {
        'status': False,
        'message': 'User does not exist',
    }

    user = User.query.filter_by(id=int(user_id), role=Role.user).first()

    if not user:
        return jsonify(response_object), 200

    response_object['status'] = True
    response_object['message'] = 'User details retrieved successfully'
    response_object['data'] = {
        'user': user.to_json()
    }

    return jsonify(response_object), 200


@user_blueprint.route('/users/update_info', methods=['PATCH'])
@authenticate
def update_user_info(user_id):
    """Update user info"""
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.',
    }

    if not post_data:
        return jsonify(response_object), 200

    try:
        user = User.query.filter_by(id=int(user_id), role=Role.user).first()

        if not user:
            raise APIError("User does not exist")

        field_types = {
            "fullname": str, "email": str, "password": str,
            "mobile_no": str, "profile_picture": str, "dob": str,
            "gender": str, "address": str, "active": bool
        }

        post_data = field_type_validator(post_data, field_types)
        if post_data.get("email"):
            email_validator(post_data.get("email"))

        if post_data.get('password'):
            user.password = bcrypt.generate_password_hash(
                post_data.get('password'), current_app.config.get(
                    "BCRYPT_LOG_ROUNDS")
            ).decode()

        gender = str(post_data.get('gender')).lower()
        if gender:
            try:
                Gender[gender]
            except KeyError:
                raise APIError("Invalid gender {}".format(gender))

        user.fullname = post_data.get('fullname') or user.fullname
        user.email = post_data.get('email') or user.email
        user.gender = Gender[gender] if gender else user.gender
        user.profile_picture = post_data.get(
            'profile_picture') or user.profile_picture
        user.dob = post_data.get('dob') or user.dob
        user.mobile_no = post_data.get('mobile_no') or user.mobile_no
        user.active = post_data.get('active') if post_data.get(
            'active') is not None else user.active

        user.update()

        response_object['status'] = True
        response_object['message'] = 'User info updated successfully.'
        response_object['data'] = {
            'user': user.to_json()
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@user_blueprint.route('/users/update_location', methods=['PATCH'])
@authenticate
def update_user_location(user_id):
    response_object = {
        'status': False,
        'message': 'Driver does not exist',
    }
    post_data = request.get_json()
    try:
        user = User.query.filter_by(id=int(user_id), role=Role.user).first()
        if not user:
            return jsonify(response_object), 200

        field_types = {
            "latitude": float, "longitude": float, "place": str
        }

        post_data = field_type_validator(post_data, field_types)

        location = Location.query.get(user.location_id)
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

        user.location_id = location.id
        user.update()

        location_json = location.to_json()

        response_object['status'] = True
        response_object['message'] = "{0}'s location updated successfully".format(
            user.fullname)
        response_object['data'] = {
            'location': location_json
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@user_blueprint.route('/users/status/mobile', methods=['GET', 'PUT'])
@authenticate
def mobile_no_otp(user_id):
    """Get or update user's mobile no. verification status"""

    response_object = {
        'status': False,
        'message': 'Invalid payload.',
    }

    try:
        user = User.query.get(int(user_id))

        if request.method == 'GET':
            response_object['status'] = True
            response_object['message'] = 'User status retrieved successfully.'
            response_object['data'] = {
                'mobile_no_verified': user.fcm_verified
            }

            return jsonify(response_object), 200

        post_data = request.get_json()

        if not post_data:
            return jsonify(response_object), 200

        post_data = field_type_validator(post_data, {"status": bool})
        required_validator(post_data, ['status'])

        user.fcm_verified = post_data.get('status')
        user.update()

        response_object['status'] = True
        response_object['message'] = 'User status updated successfully.'
        response_object['data'] = {
            'mobile_no_verified': user.fcm_verified
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@user_blueprint.route('/users/status/email', methods=['GET', 'PUT'])
@authenticate
def email_otp(user_id):
    """Get or update user's email verification status"""

    response_object = {
        'status': False,
        'message': 'Invalid payload.',
    }

    try:
        user = User.query.get(int(user_id))

        if not user:
            raise APIError("User does not exist")

        if request.method == 'GET':
            response_object['status'] = True
            response_object['message'] = 'User status retrieved successfully.'
            response_object['data'] = {
                'email_verified': user.email_verified
            }

            return jsonify(response_object), 200

        post_data = request.get_json()

        if not post_data:
            return jsonify(response_object), 200

        post_data = field_type_validator(post_data, {"otp": int})
        required_validator(post_data, ['otp'])

        logger.info("Current OTP: {}".format((str(session.get(user.email)))))

        current_otp = session.get(user.email)

        if not current_otp:
            raise APIError("OTP has expired")

        if post_data.get('otp') != int(current_otp):
            raise APIError("Invalid OTP")

        user.email_verified = True
        user.update()

        response_object['status'] = True
        response_object['message'] = 'User status updated successfully.'
        response_object['data'] = {
            'email_verified': user.email_verified
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@user_blueprint.route('/users/otp/email', methods=['GET'])
@authenticate
def get_email_otp(user_id):
    """Send email verification OTP"""

    response_object = {
        'status': False,
        'message': 'Invalid payload.',
    }

    try:
        user = User.query.get(int(user_id))

        if user.email_verified:
            raise APIError("Email already verified")

        email_otp = random.randint(100000, 999999)

        # store otp to flask session
        session[user.email] = email_otp

        send_email(email=user.email, name=user.fullname, body=str(email_otp))

        response_object['status'] = True
        response_object['message'] = 'Email OTP sent successfully.'
        response_object['data'] = {
            'email_otp': email_otp
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        response_object['message'] = str(e)
        return jsonify(response_object), 200


@user_blueprint.route('/users/delete', methods=['DELETE'])
@authenticate
def delete_user(user_id):
    """Delete user"""
    response_object = {
        'status': False,
        'message': 'User does not exist',
    }

    try:
        user = User.query.filter_by(id=int(user_id), role=Role.user).first()

        if not user:
            raise APIError("User does not exist")

        location = Location.query.get(user.location_id)
        if location:
            location.delete()

        user.delete()

        response_object['status'] = True
        response_object['message'] = 'User deleted successfully.'

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        response_object['message'] = str(e)
        return jsonify(response_object), 200
