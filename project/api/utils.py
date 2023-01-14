import os
import random
import logging
from werkzeug.utils import secure_filename
from imagekitio.client import ImageKit
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from project.exceptions import APIError

logger = logging.getLogger(__name__)

ACCESS_PRIVATE_KEY = os.getenv('IMAGEKIT_PRIVATE_KEY')
ACCESS_PUBLIC_KEY = os.getenv('IMAGEKIT_PUBLIC_KEY')
ACCESS_URL_ENDPOINT = os.getenv('IMAGEKIT_URL_ENDPOINT')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

imagekit = ImageKit(
    private_key=ACCESS_PRIVATE_KEY,
    public_key=ACCESS_PUBLIC_KEY,
    url_endpoint=ACCESS_URL_ENDPOINT
)


def upload_file(file, file_name):
    response = imagekit.upload_file(
        file=file,
        file_name=file_name
    )

    return response


def secure_file(file) -> dict:
    filename = secure_filename(file.filename)
    filetype = file.content_type

    # save file locally
    file.save(filename)
    filesize = os.stat(filename).st_size

    return {
        "filename": filename,
        "filetype": filetype,
        "filesize": filesize
    }


def send_email(email: str, name: str, body: str):
    logger.info("Sending email to: {}".format(email))

    html_content = """
        <strong>Hi {}</strong>, <br><br> 
        Please enter the following One Time PIN (OTP) in the app: <strong>{}</strong>
    """.format(name, body)

    message = Mail(
        from_email="businesssolutiongovirtual@gmail.com",
        to_emails=email,
        subject="One Time PIN (OTP) for registration",
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info("Email sent: {}".format(response.status_code))

        return response.status_code

    except Exception as e:
        logger.error(e)
        raise APIError("Error sending email: {}".format(e))


def generate_random_string(length=10):
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(letters) for i in range(length))
