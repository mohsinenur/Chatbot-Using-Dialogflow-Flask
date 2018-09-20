from flask import Flask, request, jsonify, render_template, flash
import os
import dialogflow_v2 as dialogflow
import requests
import json
import pusher

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/bot', methods=['GET', 'POST'])
def bot():
    if request.method == 'GET':
        return render_template('index.html')

    if request.method == 'POST':
        data = request.get_json(silent=True)
        display_name = data['queryResult']['intent']['displayName']
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
        else:
            reply = {
                "fulfillmentText": 'Something went wrong in display name!',
            }
            return jsonify(reply)


@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    fulfillment_text = detect_intent_texts(project_id, "unique", message, 'en')
    response_text = {"message": fulfillment_text}

    print('text send: {}'.format(fulfillment_text))
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
