from datetime import datetime

from project import db
from project.models.user_model import Location


class Church(db.Model):
    """
    Church:
        id: int
        name: string
        opening_time: time
        closing_time: time
        address: string
        contact_no: string
        location_id: int
        image_url: string
        timestamp: datetime
    """

    __tablename__ = "church"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    opening_time = db.Column(db.Time, nullable=False)
    closing_time = db.Column(db.Time, nullable=False)
    address = db.Column(db.String(128), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(
        'location.id'), nullable=True)
    contact_no = db.Column(db.String(80), unique=True, nullable=True)
    image_url = db.Column(db.String(128), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Church {self.id} {self.name}"

    def __init__(self, name: str, opening_time: str, closing_time: str,
                 address: str, location_id: int = None,
                 contact_no: str = None, image_url: str = None):
        self.name = name
        self.opening_time = opening_time
        self.closing_time = closing_time
        self.address = address
        self.location_id = location_id
        self.contact_no = contact_no
        self.image_url = image_url

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
        location = Location.query.get(self.location_id)
        return {
            "id": self.id,
            "name": self.name,
            "opening_time": self.opening_time.strftime("%I:%M %p") if self.opening_time else None,
            "closing_time": self.closing_time.strftime("%I:%M %p") if self.closing_time else None,
            "address": self.address,
            "location": location.to_json() if location else None,
            "contact_no": self.contact_no,
            "image_url": self.image_url
        }
