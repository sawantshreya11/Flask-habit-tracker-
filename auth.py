from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import users_collection
from flask_mail import Mail, Message
import random

auth = Blueprint('auth', __name__)
mail = Mail()  # Ensure this is initialized in your app config

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('auth.register'))

        if users_collection.find_one({'email': email}):
            flash("Email already registered!", "danger")
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({'email': email, 'password': hashed_password})
        flash("Registered successfully!", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html')


  

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        otp_entered = request.form.get('otp')

        user = users_collection.find_one({'email': email})

        if 'send_otp' in request.form:
            if user and check_password_hash(user['password'], password):
                otp = str(random.randint(100000, 999999))
                session['temp_user'] = email
                session['otp'] = otp

                # Send OTP to your own email
                msg = Message("Your OTP Code",
                               sender="2022.shreya.sawant@ves.ac.in",
                              recipients=["sawantshreya647@gmail.com"])
                msg.body = f"Your OTP code for login to habit tracker app is: {otp}"
                try:
                    mail.send(msg)
                    flash("OTP sent to your email!", "info")
                except Exception as e:
                    flash(f"Email sending failed: {e}", "danger")

                return render_template('login.html', show_otp=True, email=email)
            else:
                flash("Invalid email or password!", "danger")
                return redirect(url_for('auth.login'))

        elif 'login' in request.form:
            if user and check_password_hash(user['password'], password):
                if email == session.get('temp_user') and otp_entered == session.get('otp'):
                    session['user'] = email
                    session.pop('otp', None)
                    session.pop('temp_user', None)
                    flash("Logged in successfully!", "success")
                    return redirect(url_for('main.dashboard'))
                else:
                    flash("Invalid OTP!", "danger")
                    return render_template('login.html', show_otp=True, email=email)
            else:
                flash("Invalid credentials", "danger")
                return redirect(url_for('auth.login'))

    return render_template('login.html', show_otp=False)


