import jwt
import enum
import datetime

from flask import current_app

from project import db, bcrypt

"""
    Create Models
"""


class Gender(enum.Enum):
    male = 0
    female = 1
    other = 2


class Role(enum.Enum):
    admin = 0
    user = 1
    driver = 2


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fullname = db.Column(db.String(128), nullable=False)
    mobile_no = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    gender = db.Column(db.Enum(Gender), nullable=False)
    address = db.Column(db.Text, default="", nullable=True)
    location_id = db.Column(
        db.Integer, db.ForeignKey('location.id'), nullable=True)
    profile_picture = db.Column(db.String(128), default="", nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    account_suspension = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    fcm_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    licence_verified = db.Column(db.Boolean, default=False, nullable=True)
    vehicle_verified = db.Column(db.Boolean, default=False, nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    email_otp = db.Column(db.Integer, nullable=True)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.user)

    def __repr__(self):
        return f"User {self.id} {self.username}"

    def __init__(self, fullname: str, mobile_no: str, email: str, password: str, dob: str,
                 gender: str, address: str, profile_picture: str, role: str, location_id: int = None):

        self.fullname = fullname
        self.mobile_no = mobile_no
        self.email = email
        self.password = bcrypt.generate_password_hash(
            password, current_app.config.get('BCRYPT_LOG_ROUNDS')).decode()
        self.dob = dob
        self.gender = Gender[gender]
        self.address = address
        self.profile_picture = profile_picture
        self.role = Role[role]
        self.location_id = location_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        self.timestamp = datetime.datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        location = Location.query.filter_by(id=self.location_id).first()
        return {
            "id": self.id,
            "fullname": self.fullname,
            "mobile_no": self.mobile_no,
            "email": self.email,
            "dob": self.dob.strftime("%Y-%m-%d") if self.dob else None,
            "gender": self.gender.name,
            "address": self.address,
            "location": location.to_json() if location else None,
            "profile_picture": self.profile_picture,
            "role": self.role.name,
            "active": self.active,
            "mobile_no_verified": self.fcm_verified,
            "email_verified": self.email_verified,
            "licence_verified": self.licence_verified,
            "vehicle_verified": self.vehicle_verified,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }

    def encode_auth_token(self, user_id):
        """
        Generates the Auth Token - :param user_id: - :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(
                    days=current_app.config.get('TOKEN_EXPIRATION_DAYS'),
                    seconds=current_app.config.get('TOKEN_EXPIRATION_SECONDS')
                ),
                'iat': datetime.datetime.utcnow(),
                'sub': user_id
            }
            return jwt.encode(
                payload,
                current_app.config.get('SECRET_KEY'),
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token - :param auth_token: - :return: integer|string
        """
        try:
            payload = jwt.decode(
                auth_token, current_app.config.get('SECRET_KEY'))
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'


class BlacklistToken(db.Model):
    """
    Token Model for storing JWT tokens
    """
    __tablename__ = 'blacklist_tokens'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = datetime.datetime.now()

    def __repr__(self):
        return 'id: token: {}'.format(self.token)

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def check_blacklist(auth_token):
        # check whether auth token has been blacklisted
        res = BlacklistToken.query.filter_by(token=str(auth_token)).first()
        return True if res else False

    @staticmethod
    def get_all_blacklisted_tokens():
        return BlacklistToken.query.all()

    @staticmethod
    def delete_blacklisted_token(token):
        try:
            # get the token
            blacklist_token = BlacklistToken.query.filter_by(
                token=token).first()
            # delete the token
            blacklist_token.delete()
            return {
                'status': 'success',
                'message': 'Successfully logged out.'
            }
        except Exception as e:
            return e


class Location(db.Model):
    __tablename__ = "location"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    place = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"Location {self.id} {self.user_id}"

    def __init__(self, latitude: float, longitude: float, place: str = None):
        self.latitude = latitude
        self.longitude = longitude
        self.place = place

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        self.timestamp = datetime.datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "place": self.place,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }


class Vehicle(db.Model):
    __tablename__ = "vehicle"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    vehicle_no = db.Column(db.String(128), default="", nullable=False)
    vehicle_image = db.Column(db.String(128), default="", nullable=False)
    vehicle_color = db.Column(db.String(128), default="", nullable=False)
    vehicle_brand_name = db.Column(db.String(128), default="", nullable=True)
    vehicle_plate_image = db.Column(db.String(128), default="", nullable=False)

    def __repr__(self):
        return f"Vehicle {self.id} {self.user_id}"

    def __init__(self, user_id: int, vehicle_no: str, vehicle_image: str,
                 vehicle_plate_image: str = "", vehicle_color: str = "",
                 vehicle_brand_name: str = ""):
        self.user_id = user_id
        self.vehicle_no = vehicle_no
        self.vehicle_image = vehicle_image
        self.vehicle_color = vehicle_color
        self.vehicle_brand_name = vehicle_brand_name
        self.vehicle_plate_image = vehicle_plate_image

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        self.timestamp = datetime.datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "vehicle_no": self.vehicle_no,
            "vehicle_image": self.vehicle_image,
            "vehicle_color": self.vehicle_color,
            "vehicle_brand_name": self.vehicle_brand_name,
            "vehicle_plate_image": self.vehicle_plate_image,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }


class Licence(db.Model):
    __tablename__ = "licence"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    licence_no = db.Column(db.String(128), default="", nullable=False)
    licence_image_front = db.Column(db.String(128), default="", nullable=False)
    licence_image_back = db.Column(db.String(128), default="", nullable=False)

    def __repr__(self):
        return f"Licence {self.id} {self.user_id}"

    def __init__(self, user_id: int, licence_no: str, licence_image_front: str, licence_image_back: str):
        self.user_id = user_id
        self.licence_no = licence_no
        self.licence_image_front = licence_image_front
        self.licence_image_back = licence_image_back

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        self.timestamp = datetime.datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "licence_no": self.licence_no,
            "licence_image_front": self.licence_image_front,
            "licence_image_back": self.licence_image_back,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }
