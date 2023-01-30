import os
import random
import logging

from flask import Blueprint, jsonify, request

from project import db

from project.exceptions import APIError
from project.models import Church, Location
from project.api.authentications import authenticate
from project.api.validators import field_type_validator, required_validator

logger = logging.getLogger(__name__)

church_blueprint = Blueprint('church', __name__, template_folder='templates')


@church_blueprint.route('/church/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong!'
    })


@church_blueprint.route('/church/list', methods=['GET'])
@authenticate
def get_churches(user_id):
    """Get all churches"""
    churches = Church.query.all()
    response_object = {
        'status': True,
        'data': {
            'churches': [church.to_json() for church in churches]
        }
    }
    return jsonify(response_object), 200


@church_blueprint.route('/church/get/<int:church_id>', methods=['GET'])
@authenticate
def get_church(user_id, church_id):
    """Get a single church"""
    church = Church.query.filter_by(id=church_id).first()
    if not church:
        response_object = {
            'status': False,
            'message': 'Church does not exist',
        }
        return jsonify(response_object), 200

    response_object = {
        'status': True,
        'data': {
            'church': church.to_json()
        }
    }
    return jsonify(response_object), 200


@church_blueprint.route('/church/create', methods=['POST'])
@authenticate
def create_church(user_id):
    """Create a new church"""
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    try:
        field_types = {
            "name": str, "opening_time": str, "closing_time": str,
            "contact_no": str, "address": str, "location": dict,
            "image_url": str
        }

        required_fields = list(field_types.keys())
        required_fields.remove('location')
        required_fields.remove('contact_no')
        required_fields.remove('image_url')

        post_data = field_type_validator(post_data, field_types)
        required_validator(post_data, required_fields)

        name = post_data.get('name')
        opening_time = post_data.get('opening_time')
        closing_time = post_data.get('closing_time')
        contact_no = post_data.get('contact_no')
        address = post_data.get('address')
        location = post_data.get('location')
        image_url = post_data.get('image_url')

        location_id = None

        if location:
            field_types = {
                "latitude": float, "longitude": float, "place": str
            }

            required_fields = list(field_types.keys())

            location = field_type_validator(location, field_types)
            required_validator(location, required_fields)

            loc = Location.query.filter_by(
                place=str(location.get('place')).strip()).first()

            if loc:
                loc.latitude = location.get('latitude')
                loc.longitude = location.get('longitude')

                loc.update()

            else:
                loc = Location(
                    latitude=location.get('latitude'),
                    longitude=location.get('longitude'),
                    place=location.get('place')
                )

                loc.insert()

            location_id = loc.id

        church = Church.query.filter_by(name=name).first()
        if church:
            response_object['status'] = False
            response_object['message'] = 'Church with name {} already exists'.format(
                name)
            return jsonify(response_object), 200

        church = Church(
            name=name,
            opening_time=opening_time,
            closing_time=closing_time,
            address=address,
            location_id=location_id,
            contact_no=contact_no,
            image_url=image_url
        )

        church.insert()

        response_object['status'] = True
        response_object['message'] = 'Church {} was added!'.format(
            name)
        response_object['data'] = {
            'church': church.to_json()
        }
        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@church_blueprint.route('/church/update/<int:church_id>', methods=['PATCH'])
@authenticate
def update_church(user_id, church_id):
    """Update a church"""
    post_data = request.get_json()

    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    if not post_data:
        return jsonify(response_object), 200

    try:
        field_types = {
            "name": str, "opening_time": str, "closing_time": str,
            "contact_no": str, "address": str, "location": dict,
            "image_url": str
        }

        post_data = field_type_validator(post_data, field_types)

        name = post_data.get('name')
        opening_time = post_data.get('opening_time')
        closing_time = post_data.get('closing_time')
        contact_no = post_data.get('contact_no')
        address = post_data.get('address')
        location = post_data.get('location')
        image_url = post_data.get('image_url')

        location_id = None
        if location:
            field_types = {
                "latitude": float, "longitude": float, "place": str
            }

            location = field_type_validator(location, field_types)

            loc = Location.query.filter_by(
                place=str(location.get('place')).strip()).first()

            if loc:
                loc.latitude = location.get('latitude')
                loc.longitude = location.get('longitude')

                loc.update()

            else:
                loc = Location(
                    latitude=location.get('latitude'),
                    longitude=location.get('longitude'),
                    place=location.get('place')
                )

                loc.insert()

            location_id = loc.id

        church = Church.query.filter_by(id=church_id).first()
        if not church:
            response_object['status'] = False
            response_object['message'] = 'Church does not exist'
            return jsonify(response_object), 200

        church.name = name or church.name
        church.opening_time = opening_time or church.opening_time
        church.closing_time = closing_time or church.closing_time
        church.contact_no = contact_no or church.contact_no
        church.address = address or church.address
        church.location_id = location_id or church.location_id
        church.image_url = image_url or church.image_url

        church.update()

        response_object['status'] = True
        response_object['message'] = 'Church {} was updated!'.format(
            name)
        response_object['data'] = {
            'church': church.to_json()
        }
        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200


@church_blueprint.route('/church/delete/<int:church_id>', methods=['DELETE'])
@authenticate
def delete_church(user_id, church_id):
    """Delete a church"""
    response_object = {
        'status': False,
        'message': 'Invalid payload.'
    }

    try:
        church = Church.query.filter_by(id=church_id).first()
        if not church:
            response_object['status'] = False
            response_object['message'] = 'Church does not exist'
            return jsonify(response_object), 200

        location = Location.query.filter_by(id=church.location_id).first()

        church.delete()

        if location:
            location.delete()

        response_object['status'] = True
        response_object['message'] = 'Church {} was deleted!'.format(
            church.name)
        return jsonify(response_object), 200

    except Exception as e:
        db.session.rollback()
        logger.error(e)
        response_object['message'] = 'Try again: {}'.format(str(e))
        return jsonify(response_object), 200
