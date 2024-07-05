# add_test_data.py
from app import app, db
from models import Package, PackageHistory

with app.app_context():
    db.create_all()

    package = Package(
        tracking_number="123ABC",
        dimensions="10x10x10",
        weight=1.5,
        status="In Transit",
        eta="2024-07-04"
    )

    db.session.add(package)
    db.session.commit()

    history1 = PackageHistory(
        tracking_number="123ABC",
        location="New York, NY",
        timestamp="2024-07-01T12:00:00"
    )

    history2 = PackageHistory(
        tracking_number="123ABC",
        location="Philadelphia, PA",
        timestamp="2024-07-01T08:00:00"
    )

    db.session.add(history1)
    db.session.add(history2)
    db.session.commit()
