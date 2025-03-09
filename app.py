# app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import cohere
import os
import logging
import spacy
from spacytextblob.spacytextblob import SpacyTextBlob

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mindfulchat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    chats = db.relationship('Chat', backref='user', lazy=True)
    moods = db.relationship('MoodEntry', backref='user', lazy=True)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(255))
    resource_type = db.Column(db.String(50))  # article, hotline, exercise, etc.

# Cohere API Key (replace with your actual key)
cohere_api_key = "9ugWXHUfjx1a10JgzDyBWGaetyYQwjzaMXExeqM8"
co = cohere.Client(cohere_api_key)

# Mental Health Resources (Indian-specific)
MENTAL_HEALTH_RESOURCES = [
    {
        "title": "National Institute of Mental Health and Neurosciences (NIMHANS)",
        "description": "India's leading mental health institute.",
        "url": "https://nimhans.ac.in",
        "type": "institute"
    },
    {
        "title": "Vandrevala Foundation",
        "description": "24/7 mental health helpline in India.",
        "url": "https://www.vandrevalafoundation.com",
        "type": "hotline"
    },
    {
        "title": "The Live Love Laugh Foundation",
        "description": "Mental health awareness and resources.",
        "url": "https://www.thelivelovelaughfoundation.org",
        "type": "article"
    },
    {
        "title": "Yoga for Mental Health",
        "description": "Yoga techniques to improve mental well-being.",
        "url": "https://www.artofliving.org/in-en/yoga/yoga-benefits/yoga-for-mental-health",
        "type": "exercise"
    }
]

# Chatbot Processor
class ChatbotProcessor:
    def __init__(self):
        # Load spaCy model
        self.nlp = spacy.load('en_core_web_sm')
        
        # Add SpacyTextBlob to the pipeline
        self.nlp.add_pipe('spacytextblob')

    def process_message(self, message):
        try:
            # Check for emergency keywords
            if any(word in message.lower() for word in ['suicide', 'kill myself', 'end it all', 'want to die']):
                return "I'm concerned about what you're sharing. If you're having thoughts of harming yourself, please call the National Suicide Prevention Helpline at 9152987821 immediately."

            # Analyze sentiment
            sentiment = self.analyze_sentiment(message)
            if sentiment == 'negative':
                bot_response = "I'm sorry to hear that you're feeling this way. Let's talk about it."
            elif sentiment == 'positive':
                bot_response = "I'm glad to hear that you're feeling good! How can I assist you today?"
            else:
                bot_response = "Thank you for sharing. How can I assist you today?"

            # Use Cohere to generate a response
            response = co.generate(
                model='command',
                prompt=f"You are a mental health assistant. Provide supportive and empathetic responses to users. Focus on Indian mental health resources.\n\nUser: {message}\nAssistant:",
                max_tokens=150,
                temperature=0.7,
                stop_sequences=["\n"]
            )
            bot_response += "\n\n" + response.generations[0].text.strip()

            # Check if resources should be suggested
            if self.should_suggest_resources(message):
                bot_response += "\n\nHere are some resources that might help:\n"
                for resource in MENTAL_HEALTH_RESOURCES:
                    bot_response += f"- [{resource['title']}]({resource['url']})\n"

            return bot_response
        except Exception as e:
            logging.error(f"Cohere API Error: {e}")
            return "I'm having trouble connecting to the server. Please try again."

    def should_suggest_resources(self, message):
        # Keywords or phrases that trigger resource suggestions
        resource_keywords = [
            'help', 'resources', 'support', 'therapy', 'counseling', 
            'depressed', 'anxious', 'stress', 'mental health', 
            'feeling low', 'feeling down', 'feeling sad'
        ]
        
        # Check if any keyword is in the user's message
        return any(keyword in message.lower() for keyword in resource_keywords)

    def analyze_sentiment(self, message):
        # Analyze sentiment using spaCy and TextBlob
        doc = self.nlp(message)
        
        # Access polarity from the doc
        polarity = doc._.blob.polarity
        
        if polarity < -0.1:
            return 'negative'
        elif polarity > 0.1:
            return 'positive'
        else:
            return 'neutral'
# Initialize chatbot processor
chatbot = ChatbotProcessor()

# Create database if it doesn't exist
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        bot_response = chatbot.process_message(user_message)
        
        if 'user_id' in session:
            chat_entry = Chat(
                user_id=session['user_id'],
                message=user_message,
                response=bot_response
            )
            db.session.add(chat_entry)
            db.session.commit()
        
        return jsonify({'response': bot_response})
    except Exception as e:
        logging.error(f"Error in /chat route: {e}")
        return jsonify({'response': "Sorry, I encountered an error. Please try again."})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:  
            session['user_id'] = user.id
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Invalid username or password'})
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirmPassword')

        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'})

        new_user = User(
            username=username,
            email=email,
            password=password  
        )
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        return jsonify({'success': True})
    return render_template('register.html')

@app.route('/mood-history')
def mood_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    moods = MoodEntry.query.filter_by(user_id=session['user_id']).all()
    return render_template('mood-history.html', moods=moods)

@app.route('/record-mood', methods=['POST'])
def record_mood():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    data = request.get_json()
    mood = data.get('mood')
    notes = data.get('notes')

    if not mood:
        return jsonify({'success': False, 'error': 'Mood is required'})

    try:
        new_mood = MoodEntry(
            user_id=session['user_id'],
            mood=mood,
            notes=notes
        )
        db.session.add(new_mood)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error recording mood: {e}")
        return jsonify({'success': False, 'error': 'Failed to record mood'})

@app.route('/resources')
def resources():
    resources = Resource.query.all()
    return render_template('resources.html', resources=resources)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)


