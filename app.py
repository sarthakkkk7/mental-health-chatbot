#app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import cohere
import os
import logging
from textblob import TextBlob

# Initialize Flask 
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mindfulchat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db
db = SQLAlchemy(app)

# Db Models
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
    resource_type = db.Column(db.String(50))  

# Cohere API Key
cohere_api_key = "Paste your API key here"
co = cohere.Client(cohere_api_key)

# Resources
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
    def detect_emotion(self, message):
        """
        Detect the user's emotion based on the sentiment of their message.
        """
        # Analyze sentiment
        blob = TextBlob(message)
        polarity = blob.sentiment.polarity

        # Classify emotion based on polarity
        if polarity < -0.5:
            return "sad"
        elif polarity < 0:
            return "unhappy"
        elif polarity == 0:
            return "neutral"
        elif polarity < 0.5:
            return "happy"
        else:
            return "excited"

    def get_personalized_resources(self, emotion):
        """
        Get personalized resources based on the user's emotion.
        """
        
        if emotion in ["sad", "unhappy"]:
            resources = {
                "sad": [
                    {"title": "Coping with Sadness - The Live Love Laugh Foundation", "url": "https://www.thelivelovelaughfoundation.org/find-help/coping-with-sadness"},
                    {"title": "Dealing with Depression - NIMHANS", "url": " https://nimhans.ac.in/patient-care/dealing-with-depression/"}
                ],
                "unhappy": [
                    {"title": "Managing Unhappiness - MindfulTNC", "url": "https://www.mindfultnc.com/managing-unhappiness"},
                    {"title": "Vandrevala Foundation Helpline", "url": "https://www.vandrevalafoundation.com"}
                ]
            }
            return resources.get(emotion, [])
        return []

    def should_suggest_resources(self, message):
        """
        Check if resources should be suggested based on keywords or emotional state.
        """
        # Keywords or phrases that trigger resource suggestions
        resource_keywords = [
            'help', 'resources', 'support', 'therapy', 'counseling', 
            'depressed', 'anxious', 'stress', 'mental health', 
            'feeling low', 'feeling down', 'feeling sad', 'need help'
        ]
        
        # Only suggest resources if the message contains specific keywords
        return any(keyword in message.lower() for keyword in resource_keywords)

    def process_message(self, message):
        """
        Process the user's message, detect emotion, and provide a personalized response.
        """
        try:
            # Check for emergency keywords 
            if any(word in message.lower() for word in ['suicide', 'kill myself', 'end it all', 'want to die']):
                return "I'm concerned about what you're sharing. If you're having thoughts of harming yourself, please call the National Suicide Prevention Helpline at 9152987821 immediately."

            # Detect emotion 
            emotion = self.detect_emotion(message)
            print(f"Detected emotion: {emotion}")

            # Customize response based on emotion 
            if emotion in ["sad", "unhappy"]:
                bot_response = "I'm sorry to hear that you're feeling this way. Let's talk about it. What's been on your mind?\n\n"
            elif emotion == "neutral":
                bot_response = "Thank you for sharing.\n\n"
            else:
                bot_response = "I'm glad to hear that you're feeling good! How can I assist you today?\n\n"

            # Generate a conversational response using Cohere API
            response = co.generate(
                model='command',
                prompt=f"""You are a mental health assistant designed to provide supportive, empathetic, and COMPLETE responses. Follow these guidelines:
                1. Always speak naturally like ChatGPT/DeepSeek - use conversational markers ("That sounds...", "You might...")
                2. For any suggestions:
                - Give 3-5 specific tips using numbered lists
                - Add 1-sentence explanations
                - Include full action steps (never end at colon)
                3. Emotional support framework:
                A. Validate feelings ("I understand that...")
                B. Provide complete strategies
                C. Offer optional resources ONLY if requested
                D. Ask a follow-up question
                4. Never be repetitive - vary response structures
                5. Complete all thoughts fully - no partial lists
                6. You can use emojis to enhance empathy, but don't overdo it.
                7. You can use humor, but only if it fits the context and is appropriate like tell jokes or light-hearted comments when user needs cheering up.
                8. Act similar to a therapist - be supportive, but not overly formal or clinical, don't forget of your friendly side.
                9. Be up to-date with the latest mental health trends and research and current events and also refer memes and pop culture references when appropriate.
                10. Try creating mental health awareness while being sensitive to the user's feelings.
                11. You can use Hinglish (Hindi + English) to connect with the user better, but don't overdo it.
                12. Also crack jokes in Hinglish to make the user smile and lighten the mood, make sure the jokes connect to Indian culture and are relatable to the user.
                13. Give mental health related responses in Hinglish when user sends messages in Hinglish.
                Example of GOOD response:
                "I appreciate you sharing that. Here are three complete strategies you could try:
                1. Progressive muscle relaxation: Tense/release muscle groups for 2 minutes. Helps release physical stress.
                2. Thought journaling: Write down worries then challenge their accuracy. Breaks negative cycles.
                3. 5-minute meditation: Focus on breath while counting 1-10 repeatedly. Resets mental state.
                Would you like me to walk you through one of these now, or share more options?"

               Current conversation:
               User: {message}
               Assistant:""",
                max_tokens=150,
                temperature=0.7,
                stop_sequences=["\n"]
            )
            bot_response += response.generations[0].text.strip()

            # Suggest resources only if necessary
            if self.should_suggest_resources(message):
                bot_response += "\n\nHere are some resources that might help:\n"
                personalized_resources = self.get_personalized_resources(emotion)
                for resource in personalized_resources:
                    bot_response += f"- [{resource['title']}]({resource['url']})\n"

            return bot_response
        except Exception as e:
            logging.error(f"Cohere API Error: {e}")
            return "I'm having trouble connecting to the server. Please try again."

# Start Chatbot processor
chatbot = ChatbotProcessor()

# Create database tables
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
    
    moods = MoodEntry.query.filter_by(user_id=session['user_id']).order_by(MoodEntry.timestamp).all()
    print("Moods fetched from database:", moods)
    
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
    
@app.route('/chat-history')
def chat_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    chats = Chat.query.filter_by(user_id=session['user_id']).order_by(Chat.timestamp.desc()).all()
    return render_template('chat-history.html', chats=chats)    

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
