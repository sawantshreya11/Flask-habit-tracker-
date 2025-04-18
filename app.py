import traceback
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
from collections import defaultdict
import os
from flask_mail import Mail, Message
import random
import string

app = Flask(__name__)
app.secret_key = 'ec9181b790775fe1d3a980b9bc82a156'

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/habitTracker"
mongo = PyMongo(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
#app.config['MAIL_USERNAME'] = 'sawantshreya647@gmail.com'  # You can use a dummy account
app.config['MAIL_PASSWORD'] = 'ikge mapa yuue mmyw'         # Use app password if using Gmail
app.config['MAIL_USERNAME'] = '2022.shreya.sawant@ves.ac.in'
app.config['MAIL_DEFAULT_SENDER'] = '2022.shreya.sawant@ves.ac.in'

mail = Mail(app)


# Login Manager Setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# User Class for Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data.get('email', '')
        self.username = user_data.get('username', '')
        self.password_hash = user_data['password']

    @staticmethod
    def get(user_id):
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_email(email):
        user_data = mongo.db.users.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_username(username):
        user_data = mongo.db.users.find_one({'username': username})
        if user_data:
            return User(user_data)
        return None

# ✅ Fix: Add this to register the user loader
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# ✅ Serve service worker file (sw.js)
@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js')

# ✅ Home Route (renamed to 'index' to fix BuildError)
@app.route('/')
def index():
    return render_template('index.html')

# ✅ Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        existing_user = mongo.db.users.find_one({'email': email})
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        mongo.db.users.insert_one({'email': email, 'password': hashed_pw})
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# ✅ Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = None
    email = 'sawantshreya647@gmail.com'
    correct_password = '12345'

    if request.method == 'GET':
        session.pop('otp', None)
        session.pop('otp_sent', None)
        return render_template('login.html', show_otp=False)

    if session.get('otp_sent'):
        # Step 2: OTP verification
        input_otp = request.form.get('otp')
        if input_otp == session.get('otp'):
            # ✅ OTP is correct, log in the user
            user_data = mongo.db.users.find_one({'email': email})
            if user_data:
                user = User(user_data)
                login_user(user)
                session.pop('otp', None)
                session.pop('otp_sent', None)
                return redirect(url_for('dashboard'))
            else:
                error = "User not found in DB."
        else:
            error = "Invalid OTP. Please try again."
        return render_template('login.html', show_otp=True, error=error)

    # Step 1: Email + Password check and OTP send
    entered_email = request.form.get('email')
    password = request.form.get('password')

    if entered_email != email:
        error = 'Email not recognized.'
        return render_template('login.html', show_otp=False, error=error)

    if password != correct_password:
        error = 'Incorrect password.'
        return render_template('login.html', show_otp=False, error=error)

    # Generate and send OTP
    otp = ''.join(random.choices(string.digits, k=6))
    session['otp'] = otp
    session['otp_sent'] = True
    try:
        msg = Message('Your OTP Code', recipients=[email])
        msg.body = f'Hello, your OTP for logging in to the Habit Tracker app is: {otp}'
        mail.send(msg)
        success = 'OTP sent to your email.'
    except Exception as e:
        error = f'Failed to send OTP: {str(e)}'
        print('Full email error trace:')
        traceback.print_exc()

    return render_template('login.html', show_otp=True, success=success, error=error)
# ✅ Dashboard Route
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_id = current_user.get_id()

    if request.method == 'POST':
        habit_name = request.form.get('habit')
        description = request.form.get('description')

        if habit_name:
         mongo.db.habits.insert_one({
        'habit': habit_name,
        'description': description,
        'user_id': ObjectId(user_id),
        'date': datetime.now(),
        'weekly': [False] * 7,
        'monthly': [False] * 31
    })

        return redirect(url_for('dashboard'))

    habits = list(mongo.db.habits.find({'user_id': ObjectId(user_id)}))

    summary = {}
    for habit in habits:
        date_str = habit['date'].strftime('%Y-%m-%d')
        summary[date_str] = summary.get(date_str, 0) + 1

    weekly_data = [2, 4, 3, 5, 1, 2, 6]
    monthly_data = [(i % 5) + 1 for i in range(30)]

    return render_template('dashboard.html',
                           habits=habits,
                           habit_summary=summary,
                           weekly_data=weekly_data,
                           monthly_data=monthly_data)

# ✅ Delete Habit
@app.route('/delete/<habit_id>')
@login_required
def delete(habit_id):
    mongo.db.habits.delete_one({'_id': ObjectId(habit_id)})
    return redirect(url_for('dashboard'))

# ✅ Weekly Route
@app.route('/weekly')
@login_required
def weekly():
    user_id = current_user.get_id()
    habits = list(mongo.db.habits.find({'user_id': ObjectId(user_id)}))

    # Ensure all habits have a full 7-day weekly list
    for habit in habits:
        if 'weekly' not in habit or len(habit['weekly']) != 7:
            habit['weekly'] = [False] * 7
            mongo.db.habits.update_one({'_id': habit['_id']}, {'$set': {'weekly': habit['weekly']}})

    return render_template('weekly.html', habits=habits)

# ✅ Monthly Route
@app.route('/monthly')
@login_required
def monthly():
    user_id = current_user.get_id()
    habits = list(mongo.db.habits.find({'user_id': ObjectId(user_id)}))

    # Ensure all habits have a full 31-day monthly list
    for habit in habits:
        if 'monthly' not in habit or len(habit['monthly']) != 31:
            habit['monthly'] = [False] * 31
            mongo.db.habits.update_one({'_id': habit['_id']}, {'$set': {'monthly': habit['monthly']}})

    return render_template('monthly.html', habits=habits)

# ✅ Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
@app.route('/update_weekly', methods=['POST'])
@login_required
def update_weekly():
    data = request.get_json()
    habit_id = data['habit_id']
    day_index = data['day_index']
    status = data['status']
    mongo.db.habits.update_one(
        {'_id': ObjectId(habit_id)},
        {'$set': {f'weekly.{day_index}': status}}
    )
    return jsonify({'success': True})

@app.route('/update_monthly', methods=['POST'])
@login_required
def update_monthly():
    data = request.get_json()
    habit_id = data['habit_id']
    day_index = data['day_index']
    status = data['status']
    mongo.db.habits.update_one(
        {'_id': ObjectId(habit_id)},
        {'$set': {f'monthly.{day_index}': status}}
    )
    return jsonify({'success': True})

@app.route('/send_reminder', methods=['POST'])
def send_reminder():
    habit = request.form['habit']
    email = 'sawantshreya647@gmail.com'  # Change to your real address

    msg = Message('⏰ Habit Reminder',
                  sender='2022.shreya.sawant@ves.ac.in',
                  recipients=[email])
    msg.body = f"Hey, time to stay consistent with your habit: {habit} 🌟"
    mail.send(msg)
    flash('Reminder email sent successfully!', 'success')
    return redirect('/')



# ✅ Run App
if __name__ == '__main__':
    app.run(debug=True)
