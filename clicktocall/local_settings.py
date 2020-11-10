import os

'''
Configuration Settings
'''

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER', None)
MY_IP = os.environ.get('MY_IP', 'e7f20b8d9b30.ngrok.io')
