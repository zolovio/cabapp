from datetime import datetime

from project import db
from project.models.user_model import User, Location
from project.models.trip_model import Trip


class Rating(db.Model):
    """
    Rating:
        id: int
        user_id: int
        driver_id: int
        trip_id: int
        rating: int
        feedback: text
        timestamp: datetime
    """

    __tablename__ = "rating"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    feedback = db.Column(db.Text, nullable=False, default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Rating {self.id} {self.user_id}"

    def __init__(self, user_id: int, driver_id: int, trip_id: int,
                 rating: float = 5.0, feedback: str = ""):
        self.user_id = user_id
        self.driver_id = driver_id
        self.trip_id = trip_id
        self.rating = rating
        self.feedback = feedback

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
        user = User.query.get(self.user_id)
        driver = User.query.get(self.driver_id)
        trip = Trip.query.get(self.trip_id)

        return {
            "id": self.id,
            "user": user.to_json() if user else None,
            "driver": driver.to_json() if driver else None,
            "trip": trip.to_json() if trip else None,
            "rating": self.rating,
            "feedback": self.feedback,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }

    @staticmethod
    def get_average_rating(driver_id: int):
        ratings = Rating.query.filter_by(driver_id=driver_id).all()
        if len(ratings) == 0:
            return 0.0

        average_rating = sum(
            [rating.rating for rating in ratings]) / len(ratings)

        return round(average_rating, 1)
