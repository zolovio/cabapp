from flask.cli import FlaskGroup

from project import create_app, db
from project.models import (
    User, Location, Licence, Vehicle, Church
)

app = create_app()
cli = FlaskGroup(create_app=create_app)


@cli.command()
def recreate_db():
    """Recreates a local database."""
    print("Recreating database...")
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.command()
def create_db():
    """Creates a local database."""
    print("Creating database...")
    db.create_all()
    db.session.commit()


@cli.command()
def seed_db():
    """Seeds the database."""
    print("Seeding database...")

    User(
        fullname="Super Admin",
        mobile_no="+1234567890",
        email="admin@cabby.com",
        password="greaterthaneight",
        dob="1990-01-01",
        gender="other",
        address="1234 Main Street, Manchester, NH, UK, 12345",
        profile_picture="https://ik.imagekit.io/zol0vio/admin-user-icon_uOWwzefMA.jpg",
        role="admin"
    ).insert()

    location = Location(
        latitude=53.47553794561768,
        longitude=-2.216781067620185,
        place="Manchester, UK",
    )

    location.insert()

    User(
        fullname="John Doe",
        mobile_no="+2234567890",
        email="john.doe@cabby.com",
        password="greaterthaneight",
        dob="1990-01-01",
        gender="male",
        address="",
        profile_picture="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        role="user",
        location_id=location.id
    ).insert()

    driver = User(
        fullname="Mary Jane",
        mobile_no="+3234567890",
        email="mary.jane@cabby.com",
        password="greaterthaneight",
        dob="1990-01-01",
        gender="female",
        address="1234 Main Street, Manchester, NH, UK, 12345",
        profile_picture="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        role="driver",
        location_id=location.id
    )

    driver.insert()

    Licence(
        licence_no="1234567890",
        licence_image_front="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        licence_image_back="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        user_id=driver.id
    ).insert()

    Vehicle(
        vehicle_no="1234567890",
        vehicle_image="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        vehicle_plate_image="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        user_id=driver.id
    ).insert()

    print("Database seeded!")

    Church(
        name="St. Mary's Church",
        opening_time="09:00 AM",
        closing_time="05:00 PM",
        address="1234 Main Street, Manchester, NH, UK, 12345",
        location_id=location.id,
        contact_no="+1234567890",
        image_url="https://ik.imagekit.io/zol0vio/old-church_1vbz7i0Lj.jpg"
    ).insert()


if __name__ == "__main__":
    cli()
