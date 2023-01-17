import enum
from datetime import datetime

from project import db
from project.models.user_model import User, Location


class TripStatus(enum.Enum):
    pending = 0
    active = 1
    completed = 2
    cancelled = 3


class RequestStatus(enum.Enum):
    pending = 0
    accepted = 1
    rejected = 2
    cancelled = 3


class Trip(db.Model):
    """
    Trip:
        id: int
        driver_id: int
        source_id: int
        destination_id: int
        date: date
        time: time
        status: enum
        number_of_seats: int
        pooling: bool
        timestamp: datetime
    """

    __tablename__ = "trip"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey(
        'location.id'), nullable=False)
    destination_id = db.Column(
        db.Integer, db.ForeignKey('location.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum(TripStatus), nullable=False,
                       default=TripStatus.pending)
    number_of_seats = db.Column(db.Integer, nullable=False, default=1)
    pooling = db.Column(db.Boolean, nullable=False, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Trip {self.id} {self.driver_id}"

    def __init__(self, driver_id: int, source_id: int, destination_id: int,
                 date: str, time: str, status: str, number_of_seats: int, pooling: bool):

        self.driver_id = driver_id
        self.source_id = source_id
        self.destination_id = destination_id
        self.date = date
        self.time = time
        self.status = TripStatus[status]
        self.number_of_seats = number_of_seats
        self.pooling = pooling

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        self.timestamp = datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        driver = User.query.get(self.driver_id)
        source = Location.query.get(self.source_id)
        destination = Location.query.get(self.destination_id)

        return {
            "id": self.id,
            "driver": driver.to_json() if driver else None,
            "source": source.to_json() if source else None,
            "destination": destination.to_json() if destination else None,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "time": self.time.strftime("%I:%M %p") if self.time else None,
            "status": self.status.name,
            "number_of_seats": self.number_of_seats,
            "pooling": self.pooling,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }


class TripPassenger(db.Model):
    """
    TripPassenger:
        id: int
        trip_id: int
        passenger_id: int
        source_id: int
        destination_id: int
        seats_booked: int
        request_status: enum
        timestamp: datetime
    """

    __tablename__ = "trip_passenger"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    passenger_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey(
        'location.id'), nullable=False)
    destination_id = db.Column(
        db.Integer, db.ForeignKey('location.id'), nullable=False)
    seats_booked = db.Column(db.Integer, nullable=False, default=1)
    request_status = db.Column(
        db.Enum(RequestStatus), nullable=False, default=RequestStatus.pending)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"TripPassenger {self.id} {self.trip_id} {self.passenger_id}"

    def __init__(self, trip_id: int, passenger_id: int,
                 source_id: int, destination_id: int, seats_booked: int):

        self.trip_id = trip_id
        self.passenger_id = passenger_id
        self.source_id = source_id
        self.destination_id = destination_id
        self.seats_booked = seats_booked

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        self.timestamp = datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_json(self):
        trip = Trip.query.get(self.trip_id)
        source = Location.query.get(self.source_id)
        destination = Location.query.get(self.destination_id)

        return {
            "id": self.id,
            "passenger_id": self.passenger_id,
            "trip": trip.to_json() if trip else None,
            "source": source.to_json() if source else None,
            "destination": destination.to_json() if destination else None,
            "seats_booked": self.seats_booked,
            "request_status": self.request_status.name,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }
