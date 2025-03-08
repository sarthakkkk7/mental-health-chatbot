# database_setup.py
from app import app, db, User, Chat, MoodEntry, Resource
from werkzeug.security import generate_password_hash
import datetime

with app.app_context():
    db.create_all()
    
    if User.query.count() == 0:
        print("Creating sample data...")
        
        admin = User(
            username="admin",
            email="admin@mindfulchat.com",
            password_hash=generate_password_hash("adminpassword")
        )
        
        test_user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("testpassword")
        )
        
        db.session.add_all([admin, test_user])
        db.session.commit()
        
        print("Sample data created successfully!")
    else:
        print("Database already contains data. No changes made.")

