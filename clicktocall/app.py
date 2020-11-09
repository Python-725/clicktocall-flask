from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
import os, base64, uuid

from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from twilio.rest import Client

# Declare and configure application
app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')


# Route for Click to Call demo page.
@app.route('/')
def index():
    return render_template('index.html',
                           configuration_error=None)


sessionID_to_callsid = {}
sessionID_to_destNo = {}


# Generate random session id for conference
def get_session_id():
    return uuid.uuid4().hex


def get_client():
    try:
        twilio_client = Client(app.config['TWILIO_ACCOUNT_SID'],
                               app.config['TWILIO_AUTH_TOKEN'])
        return twilio_client
    except Exception as e:
        msg = f"Missing configuration variable: {e}"
        return jsonify({'error': msg}), 400


# Voice Request URL
@app.route('/call', methods=['POST'])
def call():
    # Get phone number we need to call
    source_number = request.form.get('source_number', None)
    destination_number = request.form.get('dest_number', None)
    print(f"Call Request received! source_number:{source_number}, destination_number:{destination_number}")

    if not source_number or not destination_number:
        msg = "Missing phone number value. Expected params source_number and destination_number"
        return jsonify({'error': msg}), 400

    twilio_client = get_client()
    resp = VoiceResponse()
    try:
        session_id = get_session_id()
        call = twilio_client.calls.create(record=True,
                                          from_=app.config['TWILIO_CALLER_ID'],
                                          to=source_number,
                                          url='http://2798e8db9536.ngrok.io/outbound/' + str(session_id)
                                          # url_for('.outbound', _external=True)
                                          )
        sessionID_to_callsid[session_id] = call.sid
        sessionID_to_destNo[session_id] = destination_number
        print(str(resp))
    except Exception as e:
        app.logger.error(e)
        message = e.msg if hasattr(e, 'msg') else str(e)
        return jsonify({'error': message}), 400

    return jsonify({'message': 'Call incoming!'})


@app.route('/outbound/<string:session_id>', methods=['GET', 'POST'])
def outbound_conf(session_id):
    print("Outbound Request received:", session_id)
    response = VoiceResponse()

    # Start our <Gather> verb
    gather = Gather(num_digits=1, action='/conference/' + session_id)
    gather.say('Please Press 1 to connect to destination. Press 2 to end the call.')
    response.append(gather)

    # If the user doesn't select an option, redirect them into a loop
    # response.redirect('/outbound/' + call_session_id)

    print(str(response))
    return str(response)


# +918698583414
# +919404041811
# +918767805516


@app.route('/conference/<string:session_id>', methods=['GET', 'POST'])
def conference(session_id):
    print("## Conference request received, session id:{} Making a conference call", session_id)
    """Processes results from the <Gather> prompt in /voice"""
    # Start our TwiML response
    resp = VoiceResponse()

    # If Twilio's request to our app included already gathered digits,
    # process them
    if 'Digits' in request.values:
        # Get which digit the caller chose
        choice = request.values['Digits']

        # <Say> a different message depending on the caller's choice
        if choice == '1':
            resp.say('Adding destination number to the conference!')
            # Uncomment this code and replace the number with the number you want
            # your customers to call.

            # dial = Dial()
            # dial.conference(session_id,
            #                 waitUrl='',
            #                 status_callback_event="leave")
            # resp.append(dial)

            # dial = Dial()
            # dial.conference(session_id)
            # resp.append(dial)

            resp.redirect('/add-user/' + session_id)
            print(str(resp))
            return str(resp)
        elif choice == '2':
            resp.say('You chose to end call. Thank you for calling, have a nice day!')
            # End the call with <Hangup>
            resp.hangup()
            print(str(resp))
            return str(resp)
        else:
            # If the caller didn't choose 1 or 2, apologize and ask them again
            resp.say("Sorry, I don't understand that choice.")

    # resp.hangup()
    # print(str(resp))
    # If the user didn't choose 1 or 2 (or anything), send them back to /voice
    resp.redirect('/outbound/' + session_id)

    print(str(resp))
    return str(resp)


@app.route('/add-user/<string:session_id>', methods=['POST'])
def add_user(session_id):
    print("## Add user request received, session id:{}", session_id)

    destination_number = sessionID_to_destNo[session_id]
    print("Attemtping to add phone number to call: " + destination_number)

    client = get_client()
    resp = VoiceResponse()

    dial = Dial()
    dial.conference(destination_number)
    resp.append(dial)

    participant = client.conferences(destination_number).participants.create(
        from_=app.config['TWILIO_CALLER_ID'],
        to=destination_number,
        conference_status_callback='http://2798e8db9536.ngrok.io/leave/' + session_id,
        conference_status_callback_event="leave")

    print(participant)
    return str(resp)


@app.route('/leave/<string:session_id>', methods=['GET', 'POST'])
def leave(session_id):
    event = request.values['SequenceNumber']
    conference_sid = request.values['ConferenceSid']
    print("Leave call request:", conference_sid, event, session_id)
    if request.values['StatusCallbackEvent'] == 'participant-leave':
        print("A Participant Left Call")

    resp = VoiceResponse()
    return str(resp)


# Route for Landing Page after deploy.
@app.route('/landing.html')
def landing():
    print("Get Request received!")
    return render_template('landing.html',
                           configuration_error=None)
