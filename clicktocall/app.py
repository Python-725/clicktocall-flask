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
sessionID_to_confsid = {}
sessionID_to_destNo = {}


# +918698583414
# +919404041811
# +918767805516


# Generate random session id for conference
def get_session_id(source_number, destination_number):
    return 'Conf' + destination_number + '-' + uuid.uuid4().hex


def get_client():
    try:
        twilio_client = Client(app.config['TWILIO_ACCOUNT_SID'],
                               app.config['TWILIO_AUTH_TOKEN'])
        return twilio_client
    except Exception as e:
        msg = f"Missing configuration variable: {e}"
        return jsonify({'error': msg}), 400


# Voice Request URL
@app.route('/join_conference', methods=['GET', 'POST'])
@app.route('/call_number', methods=['GET', 'POST'])
def join_conference():
    # Get phone numbers from request
    source_number = request.form.get('source_number', None)
    dest_number = request.form.get('dest_number', None)

    print(f"Call Request received! source_number:{source_number}, dest_number:{dest_number}")

    if not source_number or not dest_number:
        msg = "Missing phone number value. Expected params source_number and dest_number"
        return jsonify({'error': msg}), 400

    try:
        twilio_client = get_client()
        session_id = get_session_id(source_number, dest_number)

        call = twilio_client.calls.create(record=True,
                                          from_=app.config['TWILIO_NUMBER'],
                                          to=source_number,
                                          url='https://3.137.150.83:8001/voip/api_voip/voip_callback/' + str(session_id),
                                          status_callback_event=['completed'],
                                          status_callback='https://3.137.150.83:8001/voip/api_voip/complete_call/' + str(session_id)
                                          )
        sessionID_to_callsid[session_id] = call.sid
        sessionID_to_destNo[session_id] = dest_number
        print("Initiated a Source number Call, session_id:", session_id)
    except Exception as e:
        message = e.msg if hasattr(e, 'msg') else str(e)
        return jsonify({'error': message}), 400

    return jsonify({'message': 'Success!'})


@app.route('/voip_callback/<string:session_id>', methods=['GET', 'POST'])
def voip_callback(session_id):
    print("## Conference request received, session id:{} Making a conference call", session_id)

    """Processes results from the <Gather> prompt in /voice"""
    resp = VoiceResponse()

    # If Twilio's request to our app included already gathered digits, process them
    if 'Digits' in request.values:
        # Get which digit the caller chose
        choice = request.values['Digits']

        # Say a different message depending on the caller's choice
        if choice == '1':
            resp.say('Adding destination number to the conference!')
            resp.redirect('https://3.137.150.83:8001/voip/api_voip/add-user/' + session_id)
            print(str(resp))
            return jsonify(resp)
        elif choice == '2':
            resp.say('Thank you for calling, have a nice day!')
            # End the call with <Hangup>
            resp.hangup()
            print(str(resp))
            return jsonify(resp)
        else:
            # If the caller didn't choose 1 or 2, apologize and ask them again
            resp.say("Sorry, I don't understand that choice.")
    else:
        # Get user input
        gather = Gather(num_digits=1, action='/voip_callback/' + session_id)
        gather.say('Please Press 1 to connect to destination. Press 2 to end the call.')
        resp.append(gather)

    # If the user didn't choose 1 or 2 (or anything), repeat the message
    resp.redirect('https://3.137.150.83:8001/voip/api_voip/voip_callback/' + session_id)

    print(str(resp))
    return jsonify(resp)


@app.route('/add-user/<string:session_id>', methods=['POST'])
def add_user_to_conf(session_id):
    print("# Add user request received, session id:{}", session_id)
    destination_number = sessionID_to_destNo.get(session_id)
    print("Attemtping to add phone number to call: " + destination_number)

    client = get_client()
    resp = VoiceResponse()

    dial = Dial()
    dial.conference(destination_number)
    resp.append(dial)

    participant = client.conferences(destination_number).participants.create(
        from_=app.config['TWILIO_NUMBER'],
        to=destination_number,
        conference_status_callback='https://3.137.150.83:8001/voip/api_voip/leave/' + session_id,
        conference_status_callback_event="leave")

    print(participant)
    return str(resp)


@app.route('/leave/<string:session_id>', methods=['GET', 'POST'])
def leave(session_id):
    event = request.values['SequenceNumber']
    conference_sid = request.values['ConferenceSid']

    sessionID_to_confsid[session_id] = conference_sid
    print("Leave call request:", conference_sid, event, session_id)

    if request.values['StatusCallbackEvent'] == 'participant-leave':
        print("A Participant Left Call")
        client = get_client()
        # ends conference call if only 1 participant left
        participants = client.conferences(conference_sid).participants
        if len(participants.list()) == 1:
            client.conferences(conference_sid).update(status='completed')
            print("Call ended")
        # ends conference call if original caller leaves before callee picks up
        elif len(participants.list()) == 0 and event == '2':
            client.calls(sessionID_to_callsid.get(session_id)).update(status='completed')
        print("Call ended")

    resp = VoiceResponse()
    return str(resp)


# this is an endpoint to end the conference call if the callee rejects the call
@app.route('/complete_call/<string:call_session_id>', methods=['GET', 'POST'])
def complete_call(call_session_id):
    print("## Ending conference call, callee rejected call")
    client = get_client()
    global sessionID_to_confsid
    participants = client.conferences(sessionID_to_confsid.get(call_session_id)).participants

    # only does so if 1 participant left in the conference call (i.e. the caller)
    if len(participants.list()) == 1:
        client.conferences(sessionID_to_confsid.get(call_session_id)).update(status='completed')
        print("Call ended")
    data = {
        "status_code": 200,
    }
    resp = jsonify(data)
    return resp


# Route for Landing Page after deploy.
@app.route('/landing.html')
def landing():
    print("Get Request received!")
    return render_template('landing.html',
                           configuration_error=None)
