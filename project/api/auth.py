import logging
from flask import jsonify, request, Blueprint

from project import db, bcrypt
from project.api.authentications import authenticate
from project.api.validators import email_validator, field_type_validator, required_validator
from project.models import Role, Gender, User, BlacklistToken, Vehicle, Licence
from project.exceptions import APIError

auth_blueprint = Blueprint('auth', __name__, template_folder='templates')
logger = logging.getLogger(__name__)


@auth_blueprint.route('/users/auth/access_token', methods=['GET'])
@authenticate
def get_access_token(user_id):
    """Get access token"""
    user = User.query.filter_by(id=int(user_id)).first()
    if not user:
        response_object = {
            'status': False,
            'message': 'User does not exist',
        }
        return jsonify(response_object), 200

    auth_token = user.encode_auth_token(user.id)
    if auth_token:
        response_object["status"] = True
        response_object["message"] = "Access token generated successfully."
        response_object["data"] = {
            "auth_token": auth_token.decode('utf-8'),
            "id": user.id,
            "role": user.role.name,
        }

        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/login', methods=['POST'])
def login():
    """Login user"""
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    try:
        field_types = {"mobile_no": str, "password": str}
        required_fields = list(field_types.keys())

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        mobile_no = post_data.get('mobile_no')
        password = post_data.get('password')

        user = User.query.filter_by(mobile_no=mobile_no).first()

        if not user:
            response_object['message'] = 'Phone number or password is incorrect.'
            return jsonify(response_object), 200

        if bcrypt.check_password_hash(user.password, password.encode('utf-8')):
            if user.account_suspension:
                response_object['message'] = 'Account is suspended by admin.'
                return jsonify(response_object), 200

            user.active = True
            user.update()

            auth_token = user.encode_auth_token(user.id)
            if auth_token:
                response_object["status"] = True
                response_object["message"] = "User logged in successfully."
                response_object["data"] = {
                    "id": user.id,
                    "role": user.role.name,
                    "auth_token": auth_token.decode('utf-8'),
                }

                return jsonify(response_object), 200

        else:
            response_object['message'] = 'Phone number or password is incorrect.'
            return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: ' + str(e)
        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/logout', methods=['GET'])
@authenticate
def logout(user_id):
    """Logout user"""
    # get auth token
    auth_header = request.headers.get('Authorization')
    auth_token = auth_header.split(" ")[1]

    try:
        # blacklist token
        blacklist_token = BlacklistToken(token=auth_token)
        blacklist_token.insert()

        user = User.query.filter_by(id=int(user_id)).first()
        user.active = False
        user.update()

        response_object = {
            'status': True,
            'message': 'User logged out successfully.'
        }
        return jsonify(response_object), 200

    except Exception as e:
        logger.error(e)
        db.session.rollback()
        response_object = {
            'status': False,
            'message': str(e)
        }
        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/register', methods=['POST'])
def register():
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    field_types = {
        "fullname": str, "email": str, "mobile_no": str,
        "password": str, "role": str, "dob": str,
        "gender": str, "profile_pic": str, "address": str,
        "vehicle": dict, "licence": dict
    }

    post_data = field_type_validator(post_data, field_types)
    required_fields = list(field_types.keys())
    required_fields.remove('profile_pic')

    # check role
    role = str(post_data.get('role')).lower()

    try:
        Role[role]
    except KeyError:
        raise APIError('Invalid role {}.'.format(role))

    if Role[role] != Role.driver:
        required_fields.remove('address')

    required_fields.remove('vehicle')
    required_fields.remove('licence')

    required_validator(post_data, required_fields)
    email_validator(post_data["email"])

    gender = str(post_data.get('gender')).lower()
    try:
        Gender[gender]
    except KeyError:
        raise APIError('Invalid gender {}.'.format(gender))

    fullname = post_data.get('fullname')
    email = post_data.get('email')
    mobile_no = post_data.get("mobile_no")
    password = post_data.get('password')
    dob = post_data.get('dob')
    profile_pic = post_data.get('profile_pic')
    address = post_data.get('address')

    try:
        user = User.query.filter_by(mobile_no=mobile_no, email=email).first()

        if user:
            response_object['message'] = 'Mobile number already exists.'
            return jsonify(response_object), 200

        new_user = User(
            fullname=fullname,
            email=email,
            mobile_no=mobile_no,
            password=password,
            dob=dob,
            gender=gender,
            profile_picture=profile_pic,
            role=role,
            address=address
        )

        if Role[role] == Role.driver:
            vehicle = post_data.get('vehicle')
            licence = post_data.get('licence')

            field_types = {
                "vehicle_no": str, "vehicle_image": str,
                "vehicle_plate_image": str, "licence_no": str,
                "licence_image": str
            }

            vehicle = field_type_validator(vehicle, field_types)
            licence = field_type_validator(licence, field_types)

            if licence:
                required_fields = ['licence_no', 'licence_image']
                required_validator(licence, required_fields)

                Licence(
                    user_id=new_user.id,
                    licence_no=licence.get('licence_no'),
                    licence_image=licence.get('licence_image')
                ).insert()

            if vehicle:
                required_fields = ['vehicle_no',
                                   'vehicle_image', 'vehicle_plate_image']
                required_validator(vehicle, required_fields)

                Vehicle(
                    user_id=new_user.id,
                    vehicle_no=vehicle.get('vehicle_no'),
                    vehicle_image=vehicle.get('vehicle_image'),
                    vehicle_plate_image=vehicle.get('vehicle_plate_image')
                ).insert()

        new_user.insert()

        auth_token = new_user.encode_auth_token(new_user.id)
        response_object['status'] = False
        response_object['message'] = 'Successfully registered as {}.'.format(
            role)
        response_object['data'] = {
            'auth_token': auth_token.decode('utf-8'),
            'id': new_user.id
        }

        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@auth_blueprint.route('/users/auth/status', methods=['GET'])
@authenticate
def get_user_status(user_id):
    """Get user status"""
    user = User.query.filter_by(id=int(user_id)).first()

    response_object = {
        'status': False,
        'message': 'User not found.'
    }

    if user:
        response_object['status'] = True
        response_object['message'] = 'User status.'
        response_object['data'] = {
            'active': user.active,
            'role': user.role
        }

    return jsonify(response_object), 200
