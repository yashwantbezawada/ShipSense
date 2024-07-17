from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, Date, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Database connection string
db_connection_string = os.getenv('SQL_CONNECTION_STRING')
if not db_connection_string:
    logging.error("SQL_CONNECTION_STRING is not set. Please check your .env file.")
    exit(1)

# Log the connection string (for debugging purposes, but avoid logging sensitive information in production)
logging.info(f"DB Connection String: {db_connection_string}")

# Initialize the SQLAlchemy engine
engine = create_engine(db_connection_string)
Base = declarative_base()

# Define the Packages table
class Package(Base):
    __tablename__ = 'Packages'
    id = Column(Integer, primary_key=True)
    tracking_number = Column(String(50), unique=True, nullable=False)
    dimensions = Column(String(100))
    weight = Column(DECIMAL(10, 2))
    status = Column(String(50))
    eta = Column(Date)
    last_update = Column(DateTime, server_default=func.now())

# Define the PackageHistory table
class PackageHistory(Base):
    __tablename__ = 'PackageHistory'
    id = Column(Integer, primary_key=True)
    tracking_number = Column(String(50), ForeignKey('Packages.tracking_number'))
    location = Column(String(100))
    timestamp = Column(DateTime, server_default=func.now())

# Create the tables
Base.metadata.create_all(engine)

# Insert test data
Session = sessionmaker(bind=engine)
session = Session()

# Insert test data into Packages table
test_package = Package(
    tracking_number='123ABC',
    dimensions='10x10x10',
    weight=5.0,
    status='In Transit',
    eta='2024-07-10'
)
session.add(test_package)

# Insert test data into PackageHistory table
test_history1 = PackageHistory(tracking_number='123ABC', location='New York, NY')
test_history2 = PackageHistory(tracking_number='123ABC', location='Philadelphia, PA')
test_history3 = PackageHistory(tracking_number='123ABC', location='Baltimore, MD')
session.add_all([test_history1, test_history2, test_history3])

# Commit the changes
session.commit()

logging.info("Database schema created and test data inserted successfully")
