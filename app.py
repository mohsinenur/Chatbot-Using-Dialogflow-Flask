from flask import Flask, render_template, jsonify, flash, redirect, url_for, session, request, logging, make_response
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField
from passlib.hash import sha256_crypt
from functools import wraps
from flask_mail import Mail, Message
from wtforms.fields.html5 import EmailField
import dialogflow_v2 as dialogflow
import requests
import json
import os
import random
import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Config MySQL
mysql = MySQL()
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ccbot_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize the app for use with this MySQL class
mysql.init_app(app)


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, *kwargs)
        else:
            flash('Unauthorized, Please logged in', 'danger')
            return redirect(url_for('login'))

    return wrap


def not_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            flash('Unauthorized, You logged in', 'danger')
            return redirect(url_for('index'))
        else:
            return f(*args, *kwargs)

    return wrap


class LoginForm(Form):  # Create Login Form
    user = StringField('', [validators.length(min=1)],
                       render_kw={'autofocus': True, 'placeholder': 'Email/Phone'})
    password = PasswordField('', [validators.length(min=3)],
                             render_kw={'placeholder': 'Password'})


# User Login
@app.route('/login', methods=['GET', 'POST'])
@not_logged_in
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        # GEt user form
        user = form.user.data
        # password_candidate = request.form['password']
        password_candidate = form.password.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE (email=%s OR mobile=%s)", [user, user])

        if result > 0:
            # Get stored value
            data = cur.fetchone()
            password = data['password']
            uid = data['id']
            name = data['first_name']

            # Compare password
            if sha256_crypt.verify(password_candidate, password):
                # passed
                session['logged_in'] = True
                session['uid'] = uid
                session['first_name'] = name
                ts = '2018-09-13 17:35:24'
                cur.execute("UPDATE users SET last_login=%s WHERE id=%s", (ts, uid))
                flash('You are now logged in', 'success')
                resp = make_response(redirect('/'))
                resp.set_cookie('id', '012345')
                return resp

            else:
                flash('Incorrect password', 'danger')
                return render_template('login.html', form=form)

        else:
            flash('User not found', 'danger')
            # Close connection
            cur.close()
            return render_template('login.html', form=form)
    return render_template('login.html', form=form)


@app.route('/out')
def logout():
    if 'uid' in session:
        # Create cursor
        cur = mysql.connection.cursor()
        uid = session['uid']
        x = '2018-09-13 17:35:24'
        cur.execute("UPDATE users SET last_login=%s WHERE id=%s", (x, uid))
        session.clear()
        flash('You are logged out', 'success')
        return redirect(url_for('index'))
    return redirect(url_for('login'))


class RegisterForm(Form):
    first_name = StringField('', [validators.length(min=1, max=50)],
                             render_kw={'autofocus': True, 'placeholder': 'First Name'})
    last_name = StringField('', [validators.length(min=1, max=50)],
                            render_kw={'autofocus': True, 'placeholder': 'Last Name'})
    email = EmailField('', [validators.DataRequired(), validators.Email(), validators.length(min=4, max=25)],
                       render_kw={'placeholder': 'Email'})
    password = PasswordField('', [validators.length(min=3)],
                             render_kw={'placeholder': 'Password'})
    mobile = StringField('', [validators.length(min=11, max=15)], render_kw={'placeholder': 'Mobile'})
    account_no = StringField('', [validators.length(min=5, max=20)], render_kw={'placeholder': 'Account No'})
    balance = StringField('', [validators.length(min=1)], render_kw={'placeholder': 'Balance'})


@app.route('/register', methods=['GET', 'POST'])
@not_logged_in
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))
        mobile = form.mobile.data
        account_no = form.account_no.data
        balance = form.balance.data

        # Create Cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(first_name, last_name, email, password, mobile) "
                    "VALUES(%s, %s, %s, %s, %s)",
                    (first_name, last_name, email, password, mobile))
        # Commit cursor
        mysql.connection.commit()

        result = cur.execute("SELECT * FROM users WHERE (email=%s)", [email, ])
        if result > 0:
            # Get stored value
            data = cur.fetchone()
            user_id = data['id']
            cur.execute("INSERT INTO account(user_id, account_no, balance) " "VALUES(%s, %s, %s)",
                        (user_id, account_no, balance))
            # Commit cursor
            mysql.connection.commit()

        # Close Connection
        cur.close()
        flash('Registration successful. You can login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/bot', methods=['GET', 'POST'])
def bot():
    if request.method == 'GET':
        if 'logged_in' in session:
            uid = session['uid']
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM messages WHERE user_id=%s ORDER BY id ASC", (uid,))
            messages = cur.fetchall()
            # Close Connection
            cur.close()
            return render_template('index.html', messages=messages)
        else:
            return render_template('index.html')

    if request.method == 'POST':
        data = request.get_json(silent=True)
        display_name = data['queryResult']['intent']['displayName']
        query_text = data['queryResult']['queryText']
        u_session_text = data['session']
        u_session_text = u_session_text.split('/')
        uid = u_session_text[4]
        if uid != 'unique':
            if display_name == 'Balance Check':
                code = random.randint(111111, 999999)
                # Create cursor
                cur = mysql.connection.cursor()
                cur.execute("UPDATE users SET email_verify_code=%s WHERE id=%s", (code, uid))
                cur.close()
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                if query_text and query_text != '':
                    s_size = len(query_text)
                    if s_size == 6:
                        # Create cursor
                        cur = mysql.connection.cursor()
                        # Get user by username
                        result = cur.execute("SELECT * FROM users WHERE (id=%s and email_verify_code=%s)",
                                             [uid, query_text])
                        cur.close()
                        if result > 0:
                            # Create cursor
                            cur = mysql.connection.cursor()
                            cur.execute("UPDATE users SET email_verify_code=%s WHERE id=%s", ('0', uid))
                            cur.close()
                            reply = {
                                "fulfillmentText": 'Write your account number...',
                            }
                            return jsonify(reply)
                        else:
                            reply = {
                                "fulfillmentText": 'Invalid code! Type again please...',
                            }
                            return jsonify(reply)
                    elif s_size == 10:
                        # Create cursor
                        cur = mysql.connection.cursor()
                        # Get user by username
                        result = cur.execute("SELECT * FROM account WHERE (user_id=%s and account_no=%s)",
                                             [uid, query_text])
                        if result > 0:
                            data = cur.fetchone()
                            balance = data['balance']
                            text_response = "Your account no " + query_text + " and Balance is " + str(balance)
                            reply = {
                                "fulfillmentText": text_response,
                            }
                            cur.close()
                            return jsonify(reply)
                        else:
                            reply = {
                                "fulfillmentText": 'Account not found! Write again please...',
                            }
                            return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Can not understand. Say that again...',
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Can not understand. Say that again...',
                    }
                    return jsonify(reply)
        else:
            if display_name == 'Email or Phone check':
                email = data['queryResult']['parameters']['email']
                mobile = data['queryResult']['parameters']['mobile']
                if email or mobile:
                    if email:
                        user_email = []
                        # matching user
                        for user in users:
                            if user['email'] == email:
                                user_email.append(user)
                        if user_email:
                            reply = {
                                "fulfillmentText": 'Please, Check your email and write 6 digit code.',
                            }
                            return jsonify(reply)
                        else:
                            reply = {
                                "fulfillmentText": 'You are not registered user!',
                            }
                            return jsonify(reply)
                    elif mobile:
                        user_mobile = []
                        # matching user
                        for user in users:
                            if user['mobile'] == mobile:
                                user_mobile.append(user)
                        if user_mobile:
                            reply = {
                                "fulfillmentText": 'Please, write verification code which sent to your number.',
                            }
                            return jsonify(reply)

                        else:
                            reply = {
                                "fulfillmentText": 'You are not registered user!',
                            }
                            return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Something went wrong in email or phone check!',
                        }
                        return jsonify(reply)
            elif display_name == 'Verify Account':
                verify_code = data['queryResult']['parameters']['verify_code']
                user_verify_code = []
                # matching code
                for user in users:
                    if user['verify_code'] == verify_code:
                        user_verify_code.append(user)
                if user_verify_code:
                    reply = {
                        "fulfillmentText": 'User matched. Write your account number...',
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Invalid code!',
                    }
                    return jsonify(reply)
            elif display_name == 'Account Number':
                account_no = data['queryResult']['parameters']['account_no']
                user_account_no = []
                # matching code
                for user in users:
                    if user['account_no'] == account_no:
                        user_account_no.append(user)
                if user_account_no:
                    user_detail = requests.get(
                        'http://127.0.0.1:5000/api_test/users?account_no={0}'.format(account_no)).content
                    user_detail = json.loads(user_detail)
                    response = """ Your account balance: {0} Taka""".format(user_detail[0]['amount'])
                    reply = {
                        "fulfillmentText": response,
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found!',
                    }
                    return jsonify(reply)
            elif display_name == 'Balance Check':
                if 'logged_in' in session:
                    reply = {
                        "fulfillmentText": 'Please, write verification code which sent to your number.',
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Please, Write your email or 11 digit phone number....',
                    }
                    return jsonify(reply)
            elif display_name == 'Default Fallback Intent':
                reply = {
                    "fulfillmentText": 'Can not understand. Say that again...',
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'Something went wrong in display name!',
                }
                return jsonify(reply)


@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    if 'logged_in' in session:
        uid = session['uid']
        fulfillment_text = detect_intent_texts(project_id, uid, message, 'en')
        response_text = {"message": fulfillment_text}
        text_session = fulfillment_text
        # Create Cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO messages(user_id, users_text, agent_text, session) " "VALUES(%s, %s, %s, %s)",
                    (uid, message, fulfillment_text, text_session))

        # Commit cursor
        mysql.connection.commit()

        # Close Connection
        cur.close()
    else:
        fulfillment_text = detect_intent_texts(project_id, "unique", message, 'en')
        response_text = {"message": fulfillment_text}
    return jsonify(response_text)


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)

        return response.query_result.fulfillment_text


@app.route('/intents', methods=['POST', 'GET'])
def intents():
    if request.method == 'GET':
        return render_template('intents.html')
    if request.method == 'POST':
        intent_name = request.form['intent_name']
        project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
        training_phrases_parts = ''
        message_texts = ''
        create_intent(project_id, intent_name, training_phrases_parts, message_texts)

        return render_template('intents.html')


def create_intent(project_id, display_name, training_phrases_parts,
                  message_texts):
    """Create an intent of the given intent type."""
    intents_client = dialogflow.IntentsClient()

    parent = intents_client.project_agent_path(project_id)
    training_phrases = []
    for training_phrases_part in training_phrases_parts:
        part = dialogflow.types.Intent.TrainingPhrase.Part(
            text=training_phrases_part)
        # Here we create a new training phrase for each provided part.
        training_phrase = dialogflow.types.Intent.TrainingPhrase(parts=[part])
        training_phrases.append(training_phrase)

    text = dialogflow.types.Intent.Message.Text(text=message_texts)
    message = dialogflow.types.Intent.Message(text=text)

    intent = dialogflow.types.Intent(
        display_name=display_name,
        training_phrases=training_phrases,
        messages=[message])

    response = intents_client.create_intent(parent, intent)
    flash('Successfully intent created.', 'success')
    print('Intent created: {}'.format(response))


users = [  # user list
    {'name': 'Mukul Ahmed',
     'mobile': '01725652630',
     'account_no': '4567890123',
     'amount': '5000',
     'verify_code': 'MNBVCX',
     'email': 'mukulseu@gmail.com'},
    {'name': 'Rahat Khan',
     'mobile': '01725652640',
     'account_no': '3456789012',
     'amount': '8000',
     'verify_code': 'ZXCVBN',
     'email': 'rahat@gmail.com'},
    {'name': 'Aminul Islam',
     'mobile': '01725652650',
     'account_no': '2345678901',
     'amount': '51000',
     'verify_code': 'ASDFGH',
     'email': 'aminul@gmail.com'},
    {'name': 'Nur Mohsin',
     'mobile': '01725652640',
     'account_no': '1234567890',
     'amount': '25000',
     'verify_code': 'QWERTY',
     'email': 'mohsin@gmail.com'}
]


@app.route('/api_test/users/all', methods=['POST', 'GET'])
def api_test():
    return jsonify(users)


@app.route('/api_test/users', methods=['POST', 'GET'])
def api_email():
    # Create an empty list for our results
    results = []
    if 'email' in request.args:
        email = request.args['email']
        for user in users:
            if user['email'] == email:
                results.append(user)
    elif 'mobile' in request.args:
        mobile = request.args['mobile']
        for user in users:
            if user['email'] == mobile:
                results.append(user)
    elif 'verify_code' in request.args:
        verify_code = request.args['verify_code']
        for user in users:
            if user['verify_code'] == verify_code:
                results.append(user)
    elif 'account_no' in request.args:
        account_no = request.args['account_no']
        for user in users:
            if user['account_no'] == account_no:
                results.append(user)
    else:
        return "Error: No email or mobile or verify_code or account_no field provided. Please specify it."
    return jsonify(results)


# run Flask app
if __name__ == "__main__":
    app.run(debug=True)
