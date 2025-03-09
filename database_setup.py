# database_setup.py
from app import app, db, User, Chat, MoodEntry, Resource
from werkzeug.security import generate_password_hash
from datetime import datetime

# In database_setup.py
with app.app_context():
    db.create_all()

    if User.query.count() == 0:
        print("Creating sample data...")

        admin = User(
            username="admin",
            email="admin@mindfulchat.com",
            password="adminpassword"  # Plain password
        )

        test_user = User(
            username="testuser",
            email="test@example.com",
            password="testpassword"  # Plain password
        )

        db.session.add_all([admin, test_user])
        db.session.commit()

        # Add sample chats
        chat1 = Chat(
            user_id=admin.id,
            message="Hello, how are you?",
            response="I'm doing well, thank you! How can I assist you today?",
            timestamp=datetime.utcnow()
        )

        chat2 = Chat(
            user_id=test_user.id,
            message="I'm feeling a bit stressed.",
            response="I'm sorry to hear that. Let's talk about what's bothering you.",
            timestamp=datetime.utcnow()
        )

        db.session.add_all([chat1, chat2])
        db.session.commit()

        # Add sample mood entries
        mood1 = MoodEntry(
            user_id=admin.id,
            mood="😊",
            notes="Feeling great today!",
            timestamp=datetime.utcnow()
        )

        mood2 = MoodEntry(
            user_id=test_user.id,
            mood="😔",
            notes="Feeling a bit down.",
            timestamp=datetime.utcnow()
        )

        db.session.add_all([mood1, mood2])
        db.session.commit()

        # Add sample resources
        resources = [
            Resource(
                title="National Institute of Mental Health and Neurosciences (NIMHANS)",
                description="India's leading mental health institute.",
                url="https://nimhans.ac.in",
                resource_type="institute"
            ),
            Resource(
                title="Vandrevala Foundation",
                description="24/7 mental health helpline in India.",
                url="https://www.vandrevalafoundation.com",
                resource_type="hotline"
            ),
            Resource(
                title="The Live Love Laugh Foundation",
                description="Mental health awareness and resources.",
                url="https://www.thelivelovelaughfoundation.org",
                resource_type="article"
            ),
            Resource(
                title="Yoga for Mental Health",
                description="Yoga techniques to improve mental well-being.",
                url="https://www.artofliving.org/in-en/yoga/yoga-benefits/yoga-for-mental-health",
                resource_type="exercise"
            )
        ]

        db.session.add_all(resources)
        db.session.commit()

        print("Sample data created successfully!")
    else:
        print("Database already contains data. No changes made.")