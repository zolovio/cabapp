import logging
import traceback

from flask import jsonify, request
from project.exceptions import APIError

logger = logging.getLogger('Alpha-AI')
logger.setLevel(logging.DEBUG)


def handle_exception(ex):
    """Error handler to handle unhandled exceptions."""

    if isinstance(ex, APIError):
        response_data = {
            "status": "failed",
            "message": str(ex)
        }

        return jsonify(response_data), 400

    if hasattr(ex, 'code') and ex.code == 404:

        response_data = {
            "status": "failed",
            "message": "Requested resource not found"
        }
        return jsonify(response_data), 404
        
    else:
        tb = traceback.format_exc()
        
        logger.error('Error: Request {} has failed with exception: {}'.format(request, repr(tb)))

        response_data = {
            "status": "failed",
            "message": "Something went wrong, please inform us if this issue did not get resolve soon",
            "error": str(ex),
        }
        return jsonify(response_data), 500