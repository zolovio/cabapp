import os
import logging

from flask import Blueprint, jsonify, request
from flask import current_app

from project.models import (
    User,
    Role,
    Gender,
    Location
)

from project import db, bcrypt
from project.exceptions import APIError
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

    user_json = user.to_json()
    location = Location.query.filter_by(user_id=user.id).first()
    user_json['location'] = location.to_json() if location else None

    response_object['status'] = True
    response_object['message'] = 'User details retrieved successfully'
    response_object['data'] = {
        'user': user_json
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

    user_json = user.to_json()
    location = Location.query.filter_by(user_id=user.id).first()
    user_json['location'] = location.to_json() if location else None

    response_object['status'] = True
    response_object['message'] = 'User details retrieved successfully'
    response_object['data'] = {
        'user': user_json
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
            "latitude": float, "longitude": float
        }

        post_data = field_type_validator(post_data, field_types)

        location = Location.query.filter_by(user_id=user.id).first()
        if not location:
            location = Location(
                user_id=user.id,
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude')
            )

            location.insert()

        else:
            location.latitude = post_data.get('latitude') or location.latitude
            location.longitude = post_data.get(
                'longitude') or location.longitude
            location.update()

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

        location = Location.query.filter_by(user_id=user.id).first()
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
