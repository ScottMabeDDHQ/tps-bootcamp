from flask import Flask
from models import Advertisement, Tracker, db
import time
import datetime

import os
DB_USERNAME = os.environ['POSTGRES_USER']
DB_PASSWORD = os.environ['POSTGRES_PASSWORD']
DB_HOST = os.environ['POSTGRES_HOST']
DB_NAME = os.environ['POSTGRES_DB']


def create_app():
    """Create a Flask application"""
    app = Flask(__name__)
    #app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST + '/' + DB_NAME
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    initialize_database(app, db)
    return app


def initialize_database(app, db):
    """Drop and restore database in a consistent state"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        first_ad = Advertisement('Discount Clothing', '/t/clothing', 15.1, '1.jpg')
        second_ad = Advertisement('Cool Hats', '/products/datadog-ringer-t-shirt', 300.1, '2.jpg')
        third_ad = Advertisement('Nice Bags', '/t/bags', 5242.1, '3.jpg')
        # add first Tracker info
        timeNow = datetime.datetime.now()
        first_tracker = Tracker(str(timeNow))
        db.session.add(first_tracker)
        db.session.add(first_ad)
        db.session.add(second_ad)
        db.session.add(third_ad)
        db.session.commit()
