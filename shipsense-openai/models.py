from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Package(db.Model):
    __tablename__ = 'packages'
    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String, unique=True, nullable=False)
    dimensions = db.Column(db.String)
    weight = db.Column(db.Numeric)
    status = db.Column(db.String)
    eta = db.Column(db.Date)
    last_update = db.Column(db.DateTime, default=db.func.current_timestamp())
