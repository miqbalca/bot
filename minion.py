#############################################################################################################################
# Author: Muhammad Iqbal                                                                                                    #
# AppName: Minion
# Version: 1.2
# Description: Minion is a BOT used to unlock Active Directory Accounts and also create Entry in Service Now for tracking   #
#############################################################################################################################

#pylint: disable= C0103, W0611, W0612, W0613, C0111, W0621, C0326, C0301, C0303, C0304, C0412
import datetime
import random
import logging
import os
import ConfigParser
from datetime import datetime, timedelta
from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
import requests

minion = Flask(__name__)

### Secret key to start session
minion.secret_key = os.urandom(24)

### Accessing Configuration file
config = ConfigParser.ConfigParser()
config.read('config.ini')

# ### Start Session before any processing of request
# @minion.before_request
# def before_request():
#     session['expiry'] = datetime.now() + timedelta(hours=4)

### Now start processing the request
@minion.route('/', methods=['POST'])
def minionReply():
    #### Setting up global variables for logs
    global mainLog, userLog
    mainLog = mylogs("minion")
    userLog = mylogs(str(request.form['From']))
    ### Variable initialization
    register = 'new'
    ### Enter Session entry for the phone number and also check the registration for the number as well
    session['from'] = str(request.form['From'])
    if 'registered' not in session:
        session['registered'] = str(checkRegistration())
    ### Make entry in the logs
    #chatlog(0, request.form['From'] + " ---> " + request.form['Body'], userLog)

    ### Create Twilio response object to be able to send a reply back
    resp = MessagingResponse()
    replyText = getReply(request.form['Body'])
    #chatlog(0, "Minion ---> " + replyText, userLog)
    resp.message(replyText)
    return str(resp)


### Process Replies
def getReply(msg):
    ### Initialize response variable
    answer = ""
    reg = session['registered']
    ### Standard Messages
    GREETINGS_KEYWORD = ("hi", "hello", "hey", "minion")
    GREETINGS_RESPONSES = ['Hello','Hi','Hey']
    general = "can I have your PIN please to start off.\n"
    note = "NOTE: If you don't have PIN please check in ServiceNow if you are registered for this service"
    greetings = " and Welcome to Self Service for Resets.\n\nMy name is Minion "
    missedcom = "I think I missed something. Lets start from beginning.\n"
    srvprovider = "Thank you for your verification. How can I help? I can assist you with the following\n"
    services = "1. Password Reset\n2. Password Unlock"
    pin = "Can you provide me with your PIN so that I can Authenticate you"
    notmatchPIN = "\nSorry you have entered an invalid PIN. \nPlease type just your PIN again"
    notRegistered = "It seems like your not Registered for this service. Please enable this service in ServiceNOW for yourself."
    servicenowERROR = "There seems to be an issue with Service Now and I am not able to check your registration.\nPlease try again later"
    ### Making incoming message all lower case
    msg = msg.lower()
    
    if session['verified'] == 'false' and session['registered'] == 'true' and session['pin'] not in msg and session['askPin'] == 'true':
        answer = notmatchPIN
        
    if session['verified'] == 'false' and str(session['registered']) == 'false' and str(session['askPin']) == 'true':
        answer = notRegistered
        
    
    if session['verified'] == 'false' and msg in GREETINGS_KEYWORD and session['askPin'] == 'false':
        answer = random.choice(GREETINGS_RESPONSES) + greetings + general + note
        session['askPin'] = 'true'
        
    if session['verified'] == 'false' and str(session['pin']) in msg and session['registered'] == 'true':
        session['verified'] = 'true'
        session['askPin'] = 'true'
        msg = "[USER ENTERED PIN]"
        answer = srvprovider + services
       
    if session['registered'] == 'NA':
        answer = servicenowERROR
    if session['verified'] == 'true':
        if msg == "1" or "reset".lower() in msg or msg == "1. Password Reset".lower():
            chatlog(0, "User asked to Reset Password", userLog)
            chatlog(0, "User asked to Reset Password", mainLog)
            answer ="Password Reset capability coming soon"
            answer = srvOption("password_reset")
	if msg == "2" or "unlock".lower() in msg or msg == "2. Password Unlock".lower():
            answer = "Password Unlock capability coming soon"
            answer = srvOption("password_unlock")

        if msg == 'y' or msg == 'yes':
            answer = "For sure"
        elif msg == 'n' or msg == 'no':
            answer = "You have yourself a good rest of the day"
    
    if answer == "":
        if session['verified'] == 'false':
            session['askPin'] = 'true'
            answer = missedcom + general + note
        elif session['verified'] == 'true':
            answer = "Sorry I didn't understand what you want me to do. Please choose from the below\n" + services
    chatlog(0, "User ---> " + msg, userLog)
    chatlog(0, "User ---> " + msg, mainLog)
    chatlog(0, "Minion ---> " + answer, userLog)
    chatlog(0, "Minion ---> " + answer, mainLog)
    return answer

### Read Log File
def read_log_file():
    content = ""
    with open(session['logFile']) as f:
        for line in f.readlines():
            content += line
    print content
    return content
### Clean up the user logs
def user_log_cleanup():
    chatlog(0, "Inside user_log_cleanup function to delete the logs", mainLog)
    return "done"
### Function to Perform Action what user is requesting
def srvOption(option):
    cart = config.get('SNOW_DEV', 'cart')
    user = config.get('SNOW_DEV', 'user')
    pwd = config.get('SNOW_DEV','pwd')
    # Data that needs to be sent for adding items to cart
    data = {"sysparm_quantity":"1","variables":{"u_requested_for":str(session['user_sys_id']),"bot":"true", "work_notes":read_log_file()}}
    # Set Headers
    headers = {"Accept":"application/json"}
    reply = "Your Request is been processed your ticket number is "
    reply2 = "\n "
    chatlog(0,"User asking for " + option , userLog)

    # Do HTTPS request
    try:
        cart = cart + config.get('SNOW_DEV',option) + '/add_to_cart'
        response = requests.post(str(cart),auth=(user, pwd), headers=headers, data=str(data))
        response.raise_for_status()
    except requests.exceptions.ConnectionError as err:
        print err
        chatlog(1, err, mainLog)
        chatlog(1, err, userLog)
    except requests.exceptions.HTTPError as err:
        print err
        chatlog(1, err, mainLog)
        chatlog(1, err, userLog)
        # Check for HTTP codes other than 200
    if response.status_code != 200:
        chatlog(1, 'User Asked for '+ option + '\nStatus: ' + str(response.status_code) + '\nHeaders: ' + response.headers + '\nError Response: ' + response.json(), mainLog)
        chatlog(1, 'User Asked for '+ option + '\nStatus: ' + str(response.status_code) + '\nHeaders: ' + response.headers + '\nError Response: ' + response.json(), userLog)
        reply =  'Something Went wrong in adding items to cart!!!'
    #reqNumber = submitCart()
    reply = reply + submitCart() + reply2
    return reply

### Function to submit cart
def submitCart():
    chatlog(0,"Submitting Cart", userLog)
    submit = config.get('SNOW_DEV', 'submit_order')
    user = config.get('SNOW_DEV', 'user')
    pwd = config.get('SNOW_DEV','pwd')
    # Set Headers
    headers = {"Accept":"application/json"}
    # Do HTTPS request
    try:
        response = requests.post(submit, auth=(user, pwd), headers=headers)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as err:
        print err
        chatlog(1, err, mainLog)
        chatlog(1, err, userLog)
    except requests.exceptions.HTTPError as err:
        print err
        chatlog(1, err, mainLog)
        chatlog(1, err, userLog)
    if response.status_code != 200:
        chatlog(1, 'User Asked for Reset\nStatus: ' + str(response.status_code) + '\nHeaders: ' + response.headers + '\nError Response: ' + response.json(), mainLog)
        chatlog(1, 'User Asked for Reset\nStatus: ' + str(response.status_code) + '\nHeaders: ' + response.headers + '\nError Response: ' + response.json(), userLog)
        return 'Something Went wrong in submitting your order!!!'
    else:
        data = response.json()
        return data[u'result']['request_number']
### Function to check Registration against ServiceNOW
def checkRegistration():
    chatlog(0,"Check User Registration", userLog)
    url = config.get('SNOW_DEV', 'url') + config.get('SNOW_DEV','regTable')
    user = config.get('SNOW_DEV', 'user')
    pwd = config.get('SNOW_DEV','pwd')
    # Set Headers
    headers = {"Accept":"application/json"}
    session['registered'] = "false"
    # Do HTTPS request
    try:
        response = requests.get(str(url), auth=(config.get('SNOW_DEV', 'user'), config.get('SNOW_DEV', 'pwd')), headers=headers)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as err:
        print err
        chatlog(1, err, mainLog)
        chatlog(1, err, userLog)
    except requests.exceptions.HTTPError as err:
        print err
        chatlog(1, err, mainLog)
        chatlog(1, err, userLog)
    # Check for HTTP codes other than 200
    if response.status_code != 200:
        chatlog(1, 'Status: ' + str(response.status_code) + '\nHeaders: ' + response.headers + '\nError Response: ' + response.json(), mainLog)
        chatlog(1, 'Status: ' + str(response.status_code) + '\nHeaders: ' + response.headers + '\nError Response: ' + response.json(), userLog)
        return 'NA'
    else:
        data = response.json()
        count = len(data[u'result'])
        session['pin'] = 'kuttey'
        session['verified'] = 'false'
        session['askPin'] = 'false'
                
        for i in range(count):
            if request.form['From'] == data[u'result'][i][u'u_phone_number']:
                session['registered'] = str(data[u'result'][i][u'u_registered'])
                session['pin'] = str(data[u'result'][i][u'u_sms_pin'])
                session['user_lan_id'] = str(data[u'result'][i][u'u_user_lan_id'])
                session['user_sys_id'] = str(data[u'result'][i][u'u_user_sysid'])
                chatlog(0, "Found User!!!\nUser: " + session['user_lan_id'] + "\nUser SYS ID: " + session['user_sys_id'] + "\nPhone Number: " + session['from'] + "\nUser PIN: *****\nRegistered: " + session['registered'], userLog)
                chatlog(0, "Found User!!!\nUser: " + session['user_lan_id'] + "\nUser SYS ID: " + session['user_sys_id'] + "\nPhone Number: " + session['from'] + "\nUser PIN: *****\nRegistered: " + session['registered'], mainLog)
    if session['registered'] == 'false':
        chatlog(0, "Not a Registered User\nPhone Number: " + session['from'] + "\nRegistered: " + session['registered'], userLog)
        chatlog(0, "Not a Registered User\nPhone Number: " + session['from'] + "\nRegistered: " + session['registered'], mainLog)
    return session['registered']

### Function to initialize the logger class
def mylogs(name):
    logDir = 'logs/'
    fileName = name + ".log"
    logger = logging.getLogger(name)
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    
    if not os.path.exists(logDir + fileName):
		file = open(logDir + fileName, 'w')
    
    handler = logging.FileHandler(logDir + fileName)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    if name != 'minion':
        session['logFile'] = logDir + fileName
    return logger

### Function to take care of logs
def chatlog(level, log, logFile):
    #### Send appropriate logs to appropriate places

    if level == 1:
        logFile.error(log)
    else:
        logFile.info(log)
   

#### Code to run through terminal, this will allow Flask to work

if __name__ == '__main__':
    minion.run()

