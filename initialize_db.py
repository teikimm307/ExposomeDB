#!/usr/bin/env python3

from app import db, app

with app.app_context():
    db.create_all()
