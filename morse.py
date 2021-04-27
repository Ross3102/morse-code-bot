import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD
from time import sleep
from datetime import datetime

from twilio.rest import Client

import config

import subprocess

import requests

client = Client(account_sid, auth_token)

fromNum = "+14405307181"
toNum = "+12019949454"

DOTLEN = 40
DASHLEN = 500
BETWEEN = 500
BETWEENWORDS = 2500

DELLEN = 40
CLEARLEN = 3000

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

ENCODINGS = [
  ".-",
  "-...",
  "-.-.",
  "-..",
  ".",
  "..-.",
  "--.",
  "....",
  "..",
  ".---",
  "-.-",
  ".-..",
  "--",
  "-.",
  "---",
  ".--.",
  "--.-",
  ".-.",
  "...",
  "-",
  "..-",
  "...-",
  ".--",
  "-..-",
  "-.--",
  "--..",
  ".----",
  "..---",
  "...--",
  "....-",
  ".....",
  "-....",
  "--...",
  "---..",
  "----.",
  "-----"
]

morseBtnPin = 10
sendBtnPin = 12
delBtnPin = 15

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering

GPIO.setup(morseBtnPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(sendBtnPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(delBtnPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

lcd = CharLCD(pin_rs=19, pin_e=16, pin_rw=None, pins_data=[21, 18, 23, 24],
numbering_mode=GPIO.BOARD,
cols=16, rows=2, dotsize=8)


#lcd.clear()
#lcd.write_string("Count:"+str(n))

def drawMessage(message):
    lcd.clear()
    if len(message) < 16:
        lcd.write_string(message)
    else:
        lcd.write_string(message[-16 - len(message) % 16:])
    lcd.write_string("_")

def typeMessage(allowed_chars=LETTERS, prefix="", spaces=True):
    sleep(1)
    
    currentLetter = ""
    message = ""

    morseBtnState = 0
    prevMorseBtnState = 0

    delBtnState = 0
    prevDelBtnState = 0

    counter = datetime.now()
    delCounter = datetime.now()

    lcd.clear()
    lcd.write_string(prefix + "_")
    while True:
        morseBtnState = GPIO.input(morseBtnPin)
        sendBtnState = GPIO.input(sendBtnPin)
        delBtnState = GPIO.input(delBtnPin)

        if sendBtnState == 1:
            return message
        # Delete button was just pressed or released
        elif delBtnState != prevDelBtnState:
            if delBtnState == 1:
                delCounter = datetime.now()
            else:
                delLength = (datetime.now() - delCounter).total_seconds() * 1000
                if delLength >= DELLEN:
                    if message != "":
                        message = message[:-1]
                    drawMessage(prefix + message)
                    counter = datetime.now()
        # Delete button is being held
        elif delBtnState == 1:
            delLength = (datetime.now() - delCounter).total_seconds() * 1000
            if delLength >= CLEARLEN:
                message = ""
                drawMessage(prefix + message)
        # The button was pressed or released:
        elif morseBtnState != prevMorseBtnState:
            length = (datetime.now() - counter).total_seconds() * 1000
            # The button was released
            if morseBtnState == 0:
                if length >= DASHLEN:
                    currentLetter += "-"
                elif length >= DOTLEN:
                    currentLetter += "."
            counter = datetime.now()

        length = (datetime.now()-counter).total_seconds()*1000

        if spaces and length > BETWEENWORDS and len(message) != 0 and message[-1] != " ":
            message += " "
            currentLetter = ""
            drawMessage(prefix + message)
        
        if length >= BETWEEN and morseBtnState == 0:
            if currentLetter in ENCODINGS:
                print(currentLetter)
                i = ENCODINGS.index(currentLetter)
                if LETTERS[i] in allowed_chars:
                    message += LETTERS[i]
                    drawMessage(prefix + message)
            currentLetter = ""

        prevMorseBtnState = morseBtnState
        prevDelBtnState = delBtnState

def main():
    global toNum
    
    while True:
        sleep(1)
        
        lcd.clear()
        lcd.write_string("F: " + fromNum)
        lcd.cursor_pos = (1, 0)
        lcd.write_string("T: " + toNum)
        
        prevDelBtnState = 0;
        delCounter = datetime.now();
        while True:
            morseBtnState = GPIO.input(morseBtnPin)
            sendBtnState = GPIO.input(sendBtnPin)
            delBtnState = GPIO.input(delBtnPin)
            if morseBtnState == 1:
                message = typeMessage()
                if message != "":
                    textMsg = client.messages.create(
                                 body=message,
                                 from_=fromNum,
                                 to=toNum)
                    lcd.clear()
                    lcd.write_string("Sent")
                    sleep(3)
                    lcd.clear()
                break
            elif sendBtnState == 1:
                response = requests.get('http://morsecodemessages.herokuapp.com/get_messages', params={"password": "leoger"})
                messages = response.json()
                for m in messages:
                    lcd.clear()
                    lcd.write_string("F: " + m["sender"])
                    lcd.cursor_pos = (1, 0)
                    for i in range(len(m["content"])):
                        c = m["content"][i]
                        if i % 16 == 0 and i > 0:
                            lcd.clear()
                            lcd.write_string(m[1][i-16:i])
                            lcd.cursor_pos = (1, 0)
                        lcd.write_string(c)
                        sleep(0.1)
                    while True:
                        if GPIO.input(sendBtnPin) == 1:
                            break
                lcd.clear()
                lcd.write_string("No more messages")
                sleep(2)
                break
            elif delBtnState != prevDelBtnState:
                if delBtnState == 0 and (datetime.now() - delCounter).total_seconds() * 1000 >= 40:
                    newNum = typeMessage("0123456789", "+1", False)
                    if len(newNum) == 10:
                        toNum = "+1" + newNum
                    break
                else:
                    delCounter = datetime.now()
            elif delBtnState == 1 and (datetime.now() - delCounter).total_seconds() * 1000 >= 3000:
                return

            prevDelBtnState = delBtnState

sleep(1)
try:
    main()
except:
    pass
lcd.clear()
lcd.close()
GPIO.cleanup()

subprocess.Popen(["shutdown", "-h", "now"])

