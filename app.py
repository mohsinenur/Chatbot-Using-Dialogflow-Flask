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
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(25)

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
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        cur.execute("UPDATE users SET web_session=%s WHERE id=%s", (0, uid))
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
            now = datetime.now()
            now_hour = now.strftime("%H")
            if 5 <= int(now_hour) < 12:
                reply = "Good Morning. I'm Emi, your virtual assistant. How can I help you?"
                return render_template('index.html', reply=reply)
            elif 12 <= int(now_hour) < 18:
                reply = "Good Afternoon. I'm Emi, your virtual assistant. How can I help you?"
                return render_template('index.html', reply=reply)
            elif 18 <= int(now_hour) < 20:
                reply = "Good Evening. I'm Emi, your virtual assistant. How can I help you?"
                return render_template('index.html', reply=reply)
            else:
                reply = "Hi... I'm Emi, your virtual assistant. How can I help you?"
                return render_template('index.html', reply=reply)

    if request.method == 'POST':
        data = request.get_json(silent=True)
        display_name = data['queryResult']['intent']['displayName']
        print(display_name)
        query_text = data['queryResult']['queryText']
        u_session_text = data['session']
        u_session_text = u_session_text.split('/')
        uid = u_session_text[4]
        print(uid)
        session_value = '0'
        if display_name == 'User Verify':
            if session_value == '0':
                reply = {
                    "fulfillmentText": 'Write your Bank ABC account no...',
                    "outputContexts": [
                      {
                        "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/userverify-followup",
                        "lifespanCount": 1,
                        "parameters": {
                          "login.original": "login",
                          "login": "login"
                        }
                      }
                    ],
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'You are already verified. How can I help you?',
                }
                return jsonify(reply)
        elif display_name == 'User Verify - Account':
            account_no = data['queryResult']['parameters']['account_no']
            # Create cursor
            cur = mysql.connection.cursor()
            # Get user by username
            result = cur.execute("SELECT * FROM account WHERE (account_no=%s)", [account_no, ])
            if result > 0:
                # Get stored value
                data = cur.fetchone()
                session_value = data['web_session']
            else:
                session_value = '0'
            if session_value == '0':
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    code = random.randint(111111, 999999)
                    # Create cursor
                    cur = mysql.connection.cursor()
                    cur.execute("UPDATE users SET verify_code=%s WHERE id=%s", (code, u_id))
                    cur.close()
                    reply = {
                        "fulfillmentText": 'Write verification code which sent to your account mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/userverify-account-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "account_no.original": account_no,
                                    "account_no": account_no
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'No account found! Write again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/userverify-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "login": "login",
                                    "login.original": "login"
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'You are already verified. How can I help you?',
                }
                return jsonify(reply)
        elif display_name == 'User Verify - Account - VCode':
            v_code = data['queryResult']['parameters']['v_code']
            v_code = str(round(v_code))
            uid = 'common'
            account_no = data['queryResult']['outputContexts'][0]['parameters']['account_no']
            # Create cursor
            cur = mysql.connection.cursor()
            # Get user by username
            result = cur.execute("SELECT * FROM account WHERE (account_no=%s)", [account_no, ])
            if result > 0:
                # Get stored value
                data = cur.fetchone()
                session_value = data['web_session']
            else:
                session_value = '0'
            if session_value == '0':
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    verify_code_details = requests.get(
                        'http://127.0.0.1:5000/api_test/users?id={0}'.format(u_id)).content
                    verify_code_details = json.loads(verify_code_details)
                    verify_code_api = verify_code_details[0]['verify_code']
                    if v_code == verify_code_api:
                        cur = mysql.connection.cursor()
                        cur.execute("UPDATE users SET web_session=%s WHERE id=%s", (1, u_id))
                        cur.close()
                        reply = {
                            "fulfillmentText": 'Your verification successful. What kind of query you have?',
                            "fulfillmentMessages": [
                                {
                                    "text": {
                                        "text": [
                                            "Your verification successful. What kind of query you have?",
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "text": {
                                        "text": [
                                            "Your verification successful. What kind of query you have?",
                                        ]
                                    },
                                    "platform": "SKYPE"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "SKYPE"
                                }
                            ],
                        }
                        return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Your verification code ' + v_code + ' not matched. Write again.',
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/userverify-account-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "number.original": account_no,
                                        "number": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/userverify-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "login.original": "login",
                                    "login": "login"
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'You are already verified. How can I help you?',
                }
                return jsonify(reply)
        elif display_name == 'Balance Check':
            if uid == 'test':
                reply = {
                    "fulfillmentText": 'I can help you with that. But first I need to verify you. Write your Bank ABC account no...',
                    "outputContexts": [
                        {
                            "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/userverify-followup",
                            "lifespanCount": 1,
                            "parameters": {
                                "login.original": "login",
                                "login": "login"
                            }
                        }
                    ],
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'Write your Bank ABC account no to know balance...',
                    "outputContexts": [
                        {
                            "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/balancecheck-followup",
                            "lifespanCount": 1,
                            "parameters": {
                                "balance": "balance",
                                "balance.original": "balance"
                            }
                        }
                    ],
                }
                return jsonify(reply)
        elif display_name == 'Balance Check - Account':
            account_no = data['queryResult']['queryText']
            # Create cursor
            cur = mysql.connection.cursor()
            # Get user by username
            result = cur.execute("SELECT * FROM account WHERE (account_no=%s)", [account_no, ])
            if result > 0:
                session_value = '1'
            else:
                session_value = '0'
            print('session value = '+str(session_value))
            if session_value == '1':
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_balance = user_detail[0]['balance']
                    reply = {
                        "fulfillmentText": 'Your balance ' + str(u_balance) + ' taka in account no ' + str(
                            account_no) + '.',
                        "fulfillmentMessages": [
                            {
                                "text": {
                                    "text": [
                                        'Your balance ' + str(u_balance) + ' taka in account no ' + str(
                                            account_no) + '.',
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "text": {
                                    "text": [
                                        'Your balance ' + str(u_balance) + ' taka in account no ' + str(
                                            account_no) + '.',
                                    ]
                                },
                                "platform": "SKYPE"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                    return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    code = random.randint(111111, 999999)
                    # Create cursor
                    cur = mysql.connection.cursor()
                    cur.execute("UPDATE users SET verify_code=%s WHERE id=%s", (code, u_id))
                    cur.close()
                    reply = {
                        "fulfillmentText": 'Write verification code which sent to your account mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/balancecheck-account-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "number": account_no,
                                    "number.original": account_no
                                }
                            }
                        ],

                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'No account found! Write again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/balancecheck-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "balance": "balance",
                                    "balance.original": "balance"
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
        elif display_name == 'Balance Check - Account - VCode':
            v_code = data['queryResult']['queryText']
            account_no = data['queryResult']['outputContexts'][0]['parameters']['number.original']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    u_balance = user_detail[0]['balance']
                    verify_code_details = requests.get(
                        'http://127.0.0.1:5000/api_test/users?id={0}'.format(u_id)).content
                    verify_code_details = json.loads(verify_code_details)
                    verify_code_api = verify_code_details[0]['verify_code']
                    if v_code == verify_code_api:
                        cur = mysql.connection.cursor()
                        cur.execute("UPDATE account SET web_session=%s WHERE account_no=%s", (1, account_no))
                        cur.close()
                        reply = {
                            "fulfillmentText": 'Your balance ' + str(u_balance) + ' taka in account no ' + str(
                                account_no) + '.',
                            "fulfillmentMessages": [
                                {
                                    "text": {
                                        "text": [
                                            'Your balance ' + str(u_balance) + ' taka in account no ' + str(
                                                account_no) + '.',
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "text": {
                                        "text": [
                                            'Your balance ' + str(u_balance) + ' taka in account no ' + str(
                                                account_no) + '.',
                                        ]
                                    },
                                    "platform": "SKYPE"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "SKYPE"
                                }
                            ],
                        }
                        return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Your verification code ' + v_code + ' not matched. Write again.',
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/balancecheck-account-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "number.original": account_no,
                                        "number": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found! Write account number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/balancecheck-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "balance": "balance",
                                    "balance.original": "balance"
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
        elif display_name == 'History':
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'Write your Bank ABC account no...',
                }
                return jsonify(reply)
        elif display_name == 'History - Account':
            q_account = data['queryResult']['queryText']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(q_account)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    code = random.randint(111111, 999999)
                    # Create cursor
                    cur = mysql.connection.cursor()
                    cur.execute("UPDATE users SET verify_code=%s WHERE id=%s", (code, u_id))
                    cur.close()
                    reply = {
                        "fulfillmentText": 'Write verification code which sent to your account mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/history-account-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "number.original": q_account,
                                    "number": q_account
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/history-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "history.original": "history",
                                    "history": "history"
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
        elif display_name == 'History - Account - VCode':
            v_code = data['queryResult']['queryText']
            account_no = data['queryResult']['outputContexts'][0]['parameters']['number.original']

            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    verify_code_details = requests.get(
                        'http://127.0.0.1:5000/api_test/users?id={0}'.format(u_id)).content
                    verify_code_details = json.loads(verify_code_details)
                    verify_code_api = verify_code_details[0]['verify_code']
                    if v_code == verify_code_api:
                        history = ''
                        fb_history = ''
                        all_deposit = requests.get(
                            'http://127.0.0.1:5000/api_test/deposit?account_no={0}'.format(account_no)).content
                        all_deposit = json.loads(all_deposit)
                        i = 1
                        for info in all_deposit:
                            amount = info['amount']
                            trx_type = info['trx_type']
                            date = info['date']
                            date = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S GMT')
                            date_d = date.strftime('%d %b, %Y')
                            date_t = date.strftime('%H:%M %p')
                            history += '<tr><td>' + str(amount) + '</td><td>' + str(trx_type) + '</td><td>' + str(
                                date_d) + ' ' + ' at ' + str(date_t) + '</td></tr>'
                            fb_history += '(' + str(i) + ') ' + str(trx_type) + ' ' + str(
                                amount) + ' taka at ' + str(date_t) + ' ' + str(date_d) + '. '
                            i += 1
                        reply = {
                            "fulfillmentText": 'Your tranjection history below '
                                               '<table class="table table-bordered">'
                                               '<thead><tr> <th>Amount</th><th>Type</th><th>Date</th></tr></thead><tbody>'
                                               + history +
                                               '</tbody></table>',
                            "fulfillmentMessages": [
                                {
                                    "text": {
                                        "text": [
                                            "Your tranjection history: " + fb_history,
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "text": {
                                        "text": [
                                            "Your tranjection history: " + fb_history,
                                        ]
                                    },
                                    "platform": "SKYPE"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "SKYPE"
                                }
                            ],
                        }
                        return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Your verification code ' + v_code + ' not matched. Write again.',
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/history-account-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "number.original": account_no,
                                        "number": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write account again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/history-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "history.original": "history",
                                    "history": "history"
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Top Up':
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'Please, Select an operator below...',
                    "fulfillmentMessages": [
                        {
                            "quickReplies": {
                                "title": "Please, select an operator below...",
                                "quickReplies": [
                                    "Grameenphone",
                                    "Airtel",
                                    "Robi",
                                    "Banglalink",
                                    "Telitalk"
                                ]
                            },
                            "platform": "FACEBOOK"
                        },
                        {
                            "quickReplies": {
                                "title": "Please, select an operator below...",
                                "quickReplies": [
                                    "Grameenphone",
                                    "Airtel",
                                    "Robi",
                                    "Banglalink",
                                    "Telitalk"
                                ]
                            },
                            "platform": "SKYPE"
                        }
                    ],
                }
                return jsonify(reply)
        elif display_name == 'Top Up - operator':
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                operator = ['airtel', 'robi', 'grameenphone', 'telitalk', 'banglalink', 'gp', 'bl']
                operator_name = data['queryResult']['parameters']['operator-name'][0]
                text_con = operator_name.lower()
                if text_con in operator:
                    reply = {
                        "fulfillmentText": 'Write your 11 digit mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-operator-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "operator-name.original": query_text,
                                    "operator-name": query_text
                                }
                            }
                        ],
                    }
                else:
                    reply = {
                        "fulfillmentText": 'Operator not found. Select again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "topup": "top up",
                                    "topup.original": "topup"
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Top Up - operator - phone':
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                mobile = data['queryResult']['parameters']['number']
                mobile = round(mobile)
                print(mobile)
                length = len(query_text)
                if length == 11:
                    reply = {
                        "fulfillmentText": "It's prepaid or postpaid?",
                        "fulfillmentMessages": [
                            {
                                "quickReplies": {
                                    "title": "It's prepaid or postpaid?",
                                    "quickReplies": [
                                        "Prepaid",
                                        "Postpaid"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "It's prepaid or postpaid?",
                                    "quickReplies": [
                                        "Prepaid",
                                        "Postpaid"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-operator-phone-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "mobile.original": query_text,
                                    "mobile": query_text
                                }
                            }
                        ],
                    }
                else:
                    reply = {
                        "fulfillmentText": 'Incorrect. Please write 11 digit mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-operator-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "operator-name.original": query_text,
                                    "operator-name": query_text
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Top Up - operator - phone - type':
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                operator_type = ['prepaid', 'postpaid', 'pre paid', 'post paid']
                op_type = data['queryResult']['parameters']['pre-post']
                # mobile = data['queryResult']['parameters']['mobile']
                text_con = query_text.lower()
                if text_con in operator_type:
                    reply = {
                        "fulfillmentText": "How much you want to topup?",
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-operator-phone-type-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "pre-post.original": query_text,
                                    "pre-post": query_text
                                }
                            }
                        ],
                    }
                else:
                    reply = {
                        "fulfillmentText": "Type not found. Select again.",
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-operator-phone-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "mobile.original": query_text,
                                    "mobile": query_text
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Top Up - operator - phone - type - amount':
            amount = data['queryResult']['outputContexts'][0]['parameters']['amount']
            op_type = data['queryResult']['outputContexts'][0]['parameters']['pre-post']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                if amount:
                    reply = {
                        "fulfillmentText": "Topup successful.",
                        "fulfillmentMessages": [
                            {
                                "text": {
                                    "text": [
                                        "Topup successful.",
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "text": {
                                    "text": [
                                        "Topup successful.",
                                    ]
                                },
                                "platform": "SKYPE"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                else:
                    reply = {
                        "fulfillmentText": "You have not sufficient amount. Write less.",
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/topup-operator-phone-type-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "pre-post.original": query_text,
                                    "pre-post": query_text
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Stop Check':
            stop_check = data['queryResult']['parameters']['stop_check']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'Write your Bank ABC account no...',
                    "outputContexts": [
                        {
                            "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/stopcheck-followup",
                            "lifespanCount": 1,
                            "parameters": {
                                "stop_check.original": query_text,
                                "stop_check": stop_check
                            }
                        }
                    ],
                }
                return jsonify(reply)
        elif display_name == 'Stop Check - Account':
            q_account = data['queryResult']['parameters']['account_no']
            q_account = str(round(q_account))
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(q_account)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    code = random.randint(111111, 999999)
                    # Create cursor
                    cur = mysql.connection.cursor()
                    cur.execute("UPDATE users SET verify_code=%s WHERE id=%s", (code, u_id))
                    cur.close()
                    reply = {
                        "fulfillmentText": 'Write verification code which sent to your account mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/stopcheck-account-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "account_no": q_account,
                                    "account_no.original": query_text,
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/stopcheck-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "stop_check": 'stop check'
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
        elif display_name == 'Stop Check - Account - VCode':
            v_code = data['queryResult']['parameters']['sv_code']
            v_code = str(round(v_code))
            account_no = data['queryResult']['outputContexts'][0]['parameters']['account_no']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    verify_code_details = requests.get(
                        'http://127.0.0.1:5000/api_test/users?id={0}'.format(u_id)).content
                    verify_code_details = json.loads(verify_code_details)
                    verify_code_api = verify_code_details[0]['verify_code']
                    if v_code == verify_code_api:
                        reply = {
                            "fulfillmentText": 'Thanks for your information. Your cheque stopped. Very soon we will contact with you.',
                            "fulfillmentMessages": [
                                {
                                    "text": {
                                        "text": [
                                            "Thanks for your information. Your cheque stopped. Very soon we will contact with you.",
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "text": {
                                        "text": [
                                            "Thanks for your information. Your cheque stopped. Very soon we will contact with you.",
                                        ]
                                    },
                                    "platform": "SKYPE"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "SKYPE"
                                }
                            ],
                        }
                        return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Your verification code ' + str(v_code) + ' not matched. Write again.',
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/stopcheck-account-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "account_no.original": query_text,
                                        "account_no": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write account again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/stopcheck-account-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "account_no": account_no,
                                    "account_no.original": query_text,
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Cheque Book Request':
            cheque_book_request = data['queryResult']['parameters']['cheque_book_request']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                reply = {
                    "fulfillmentText": 'Write your Bank ABC account no...',
                    "outputContexts": [
                        {
                            "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-followup",
                            "lifespanCount": 1,
                            "parameters": {
                                "cheque_book_request.original": query_text,
                                "cheque_book_request": cheque_book_request
                            }
                        }
                    ],
                }
                return jsonify(reply)
        elif display_name == 'Cheque Book Request - Account':
            account_no = data['queryResult']['parameters']['account_num']
            q_account = str(round(account_no))
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(q_account)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    code = random.randint(111111, 999999)
                    # Create cursor
                    cur = mysql.connection.cursor()
                    cur.execute("UPDATE users SET verify_code=%s WHERE id=%s", (code, u_id))
                    cur.close()
                    reply = {
                        "fulfillmentText": 'Write verification code which sent to your account mobile number.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-account-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "account_num.original": query_text,
                                    "account_num": q_account,
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "cheque_book_request": 'cheque book request'
                                }
                            }
                        ],
                    }
                    return jsonify(reply)
        elif display_name == 'Cheque Book Request - Account - VCode':
            v_code = data['queryResult']['parameters']['cv_code']
            v_code = str(round(v_code))
            account_no = data['queryResult']['outputContexts'][0]['parameters']['account_num']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    u_id = user_detail[0]['user_id']
                    verify_code_details = requests.get(
                        'http://127.0.0.1:5000/api_test/users?id={0}'.format(u_id)).content
                    verify_code_details = json.loads(verify_code_details)
                    verify_code_api = verify_code_details[0]['verify_code']
                    if v_code == verify_code_api:
                        reply = {
                            "fulfillmentText": 'How many pages?',
                            "fulfillmentMessages": [
                                {
                                    "quickReplies": {
                                        "title": "How many pages?",
                                        "quickReplies": [
                                            "10",
                                            "25",
                                            "50"
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "quickReplies": {
                                        "title": "How many pages?",
                                        "quickReplies": [
                                            "10",
                                            "25",
                                            "50"
                                        ]
                                    },
                                    "platform": "SKYPE"
                                }
                            ],
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-account-vcode-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "account_num.original": account_no,
                                        "account_num": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Your verification code ' + str(v_code) + ' not matched. Write again.',
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-account-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "account_num.original": account_no,
                                        "account_num": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write account again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "cheque_book_request": 'cheque book request'
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Cheque Book Request - Account - VCode - Page':
            pages = data['queryResult']['parameters']['pages']
            pages = round(pages)
            account_no = data['queryResult']['outputContexts'][0]['parameters']['account_num']
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                user_detail = requests.get(
                    'http://127.0.0.1:5000/api_test/account?account_no={0}'.format(account_no)).content
                user_detail = json.loads(user_detail)
                if user_detail:
                    page_num = [10, 20, 25, 50, 100]
                    if pages in page_num:
                        reply = {
                            "fulfillmentText": 'Your cheque request accepted.',
                            "fulfillmentMessages": [
                                {
                                    "text": {
                                        "text": [
                                            "Your cheque request accepted.",
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "FACEBOOK"
                                },
                                {
                                    "text": {
                                        "text": [
                                            "Your cheque request accepted.",
                                        ]
                                    },
                                    "platform": "SKYPE"
                                },
                                {
                                    "quickReplies": {
                                        "title": "Have more query? Select quick link below.",
                                        "quickReplies": [
                                            "Banking Query",
                                            "Top Up",
                                            "General Information"
                                        ]
                                    },
                                    "platform": "SKYPE"
                                }
                            ],
                        }
                        return jsonify(reply)
                    else:
                        reply = {
                            "fulfillmentText": 'Page number not valid. Write again.',
                            "outputContexts": [
                                {
                                    "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-account-vcode-followup",
                                    "lifespanCount": 1,
                                    "parameters": {
                                        "account_num.original": account_no,
                                        "account_num": account_no
                                    }
                                }
                            ],
                        }
                        return jsonify(reply)
                else:
                    reply = {
                        "fulfillmentText": 'Account not found. Write account again.',
                        "outputContexts": [
                            {
                                "name": "projects/customercarechatbot-d2f6c/agent/sessions/" + uid + "/contexts/chequebookrequest-followup",
                                "lifespanCount": 1,
                                "parameters": {
                                    "cheque_book_request": 'cheque book request'
                                }
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Services':
            if 'logged_in' in session:
                reply = {
                    "fulfillmentText": 'Please, write verification code which sent to your number.',
                }
                return jsonify(reply)
            else:
                service_text = data['queryResult']['parameters']['service']
                if query_text == 'Banking Query' or service_text == 'Banking Query':
                    reply = {
                        "fulfillmentText": 'What kind of query you have?',
                        "fulfillmentMessages": [
                            {
                                "quickReplies": {
                                    "title": "What kind of query you have?",
                                    "quickReplies": [
                                        "Balance Check",
                                        "History",
                                        "Stop Cheque",
                                        "Cheque Book Request"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "What kind of query you have?",
                                    "quickReplies": [
                                        "Balance Check",
                                        "History",
                                        "Stop Cheque",
                                        "Cheque Book Request"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                elif query_text == 'General Information' or service_text == 'General Information':
                    reply = {
                        "fulfillmentText": 'What kind of information?',
                        "fulfillmentMessages": [
                            {
                                "quickReplies": {
                                    "title": "What kind of information?",
                                    "quickReplies": [
                                        "About Bank",
                                        "Terms And Conditions"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "What kind of information?",
                                    "quickReplies": [
                                        "About Bank",
                                        "Terms And Conditions"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                elif query_text == 'About Bank' or service_text == 'About Bank':
                    reply = {
                        "fulfillmentText": 'BANK ABC was launched in 2007 as an associated company of one of the'
                                           ' biggest garments exporting groups in Bangladesh, Concorde Garments. '
                                           'To know more visit this link... '
                                           '<a href="http://bankabc.com" target="_blank">About Bank</a>',
                        "fulfillmentMessages": [
                            {
                                "card": {
                                    "title": "About Bank ABC",
                                    "subtitle": "BANK ABC was launched in 2007 as an associated company of one of the",
                                    "imageUri": "http://sslwireless.com/images/banner/Payment-Deed-of-Agreement.jpg",
                                    "buttons": [
                                        {
                                            "text": "Read more",
                                            "postback": "http://sslwireless.com"
                                        }
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "card": {
                                    "title": "About Bank ABC",
                                    "subtitle": "BANK ABC was launched in 2007 as an associated company of one of the",
                                    "imageUri": "http://sslwireless.com/images/banner/Payment-Deed-of-Agreement.jpg",
                                    "buttons": [
                                        {
                                            "text": "Read more",
                                            "postback": "http://sslwireless.com"
                                        }
                                    ]
                                },
                                "platform": "SKYPE"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                elif query_text == 'Terms And Conditions' or service_text == 'Terms And Conditions':
                    reply = {
                        "fulfillmentText": "Feel free to ask any question. If I can't reply your answer then "
                                           "I will help you to chat with real agent. To know more visit this link... "
                                           "<a href='http://bankabc.com' target='_blank'>Terms And Conditions</a>",
                        "fulfillmentMessages": [
                            {
                                "card": {
                                    "title": "Terms And Conditions",
                                    "subtitle": "Feel free to ask any question. If I can't reply your answer then I "
                                                "will help you to chat with real agent. To know more visit this link...",
                                    "imageUri": "http://sslwireless.com/images/banner/Payment-Deed-of-Agreement.jpg",
                                    "buttons": [
                                        {
                                            "text": "Read more",
                                            "postback": "http://sslwireless.com/recent_works.php?id=32"
                                        }
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "card": {
                                    "title": "Terms And Conditions",
                                    "subtitle": "Feel free to ask any question. If I can't reply your answer then I "
                                                "will help you to chat with real agent. To know more visit this link...",
                                    "imageUri": "http://sslwireless.com/images/banner/Payment-Deed-of-Agreement.jpg",
                                    "buttons": [
                                        {
                                            "text": "Read more",
                                            "postback": "http://sslwireless.com/recent_works.php?id=32"
                                        }
                                    ]
                                },
                                "platform": "SKYPE"
                            },
                            {
                                "quickReplies": {
                                    "title": "Have more query? Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                else:
                    reply = {
                        "fulfillmentText": "How can I help you?",
                        "fulfillmentMessages": [
                            {
                                "text": {
                                    "text": [
                                        "How can I help you?",
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "quickReplies": {
                                    "title": "Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "FACEBOOK"
                            },
                            {
                                "text": {
                                    "text": [
                                        "How can I help you?",
                                    ]
                                },
                                "platform": "SKYPE"
                            },
                            {
                                "quickReplies": {
                                    "title": "Select quick link below.",
                                    "quickReplies": [
                                        "Banking Query",
                                        "Top Up",
                                        "General Information"
                                    ]
                                },
                                "platform": "SKYPE"
                            }
                        ],
                    }
                return jsonify(reply)
        elif display_name == 'Default Fallback Intent':
            reply = {
                "fulfillmentText": 'Could not understand.',
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                            "title": "Could not understand. Please, select a quick link below.",
                            "quickReplies": [
                                "Banking Query",
                                "Top Up",
                                "General Information"
                            ]
                        },
                        "platform": "FACEBOOK"
                    },
                    {
                        "quickReplies": {
                            "title": "Could not understand. Please, select a quick link below.",
                            "quickReplies": [
                                "Banking Query",
                                "Top Up",
                                "General Information"
                            ]
                        },
                        "platform": "SKYPE"
                    }
                ],
            }
            return jsonify(reply)
        elif display_name == 'Default Welcome Intent':
            now = datetime.now()
            now_hour = now.strftime("%H")
            if 5 <= int(now_hour) < 12:
                wish = "Good Morning"
            elif 12 <= int(now_hour) < 18:
                wish = "Good Afternoon"
            elif 18 <= int(now_hour) < 20:
                wish = "Good Evening"
            else:
                wish = "Hi.."
            reply = {
                "fulfillmentText": wish + ". I'm Emi, your virtual assistant. How can I help you?",
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [
                                wish + ". I'm Emi, your virtual assistant. How can I help you?"
                            ]
                        },
                        "platform": "FACEBOOK"
                    },
                    {
                        "quickReplies": {
                            "title": "Select quick link below",
                            "quickReplies": [
                                "Banking Query",
                                "Top Up",
                                "General Information"
                            ]
                        },
                        "platform": "FACEBOOK"
                    },
                    {
                        "text": {
                            "text": [
                                wish + ". I'm Emi, your virtual assistant. How can I help you?"
                            ]
                        },
                        "platform": "SKYPE"
                    },
                    {
                        "quickReplies": {
                            "title": "Select quick link below",
                            "quickReplies": [
                                "Banking Query",
                                "Top Up",
                                "General Information"
                            ]
                        },
                        "platform": "SKYPE"
                    }
                ],
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
     'mobile': '01677531881',
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
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users")
    user_list = cur.fetchall()
    # Create an empty list for our results
    results = []
    if 'id' in request.args:
        u_id = request.args['id']
        for user in user_list:
            if user['id'] == int(u_id):
                results.append(user)
    elif 'email' in request.args:
        email = request.args['email']
        for user in user_list:
            if user['email'] == email:
                results.append(user)
    elif 'mobile' in request.args:
        mobile = request.args['mobile']
        for user in user_list:
            if user['mobile'] == mobile:
                results.append(user)
    elif 'verify_code' in request.args:
        verify_code = request.args['verify_code']
        for user in user_list:
            if user['verify_code'] == verify_code:
                results.append(user)
    else:
        return "Error: No email or mobile or verify_code field provided. Please specify it."
    return jsonify(results)


@app.route('/api_test/deposit', methods=['POST', 'GET'])
def api_deposit():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM deposit")
    deposit_list = cur.fetchall()
    # Create an empty list for our results
    results = []
    if 'account_no' in request.args:
        account_no = request.args['account_no']
        for accounts in deposit_list:
            if accounts['account_no'] == account_no:
                results.append(accounts)

    else:
        return "Error: No account_no field provided. Please specify it."
    return jsonify(results)


@app.route('/api_test/account', methods=['POST', 'GET'])
def api_account():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM account")
    deposit_list = cur.fetchall()
    # Create an empty list for our results
    results = []
    if 'account_no' in request.args:
        account_no = request.args['account_no']
        for accounts in deposit_list:
            if accounts['account_no'] == account_no:
                results.append(accounts)

    else:
        return "Error: No account_no field provided. Please specify it."
    return jsonify(results)


# run Flask app
if __name__ == "__main__":
    app.run(debug=True)
