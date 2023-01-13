from flask.cli import FlaskGroup

from project import create_app, db
from project.models.user_model import User, Location, Licence, Vehicle

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

    user = User(
        fullname="John Doe",
        mobile_no="+2234567890",
        email="john.doe@cabby.com",
        password="greaterthaneight",
        dob="1990-01-01",
        gender="male",
        address="",
        profile_picture="https://ik.imagekit.io/zol0vio/user_icon_G2tZaIWiQ.png",
        role="user"
    )

    user.insert()

    Location(
        latitude=53.47553794561768,
        longitude=-2.216781067620185,
        user_id=user.id
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
        role="driver"
    )

    driver.insert()

    Location(
        latitude=53.47553794561768,
        longitude=-2.216781067620185,
        user_id=driver.id
    ).insert()

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


if __name__ == "__main__":
    cli()
