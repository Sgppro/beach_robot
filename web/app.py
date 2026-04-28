import RPi.GPIO as GPIO
import time
import pyttsx3
import os
import speech_recognition as sr
import json
import boto3
import threading
from flask import Flask, render_template, jsonify

# --- GLOBALS & STATE ---
# Change these values anywhere in your script to move the dot automatically
current_x = 50 
current_y = 50
latest_ai_message = "Press the button to ask questions." 

def reset_message():
    global latest_ai_message
    latest_ai_message = "Press the button to ask questions."

# --- HARDWARE & AI SETUP ---
BUTTON_PIN = 26 
DEBOUNCE_TIME = 0.2

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN)

os.environ['ALSA_CARD'] = '2'

# Text to speech
engine = pyttsx3.init()
engine.setProperty('rate', 120)
engine.setProperty('volume', 1)

# Microphone setup
r = sr.Recognizer()
m = sr.Microphone()

# AWS Bedrock setup
client = boto3.client("bedrock-runtime", region_name="ap-southeast-2")
model_id = "amazon.nova-lite-v1:0"

system_prompt = """You are a friendly, helpful robotic guide stationed on a beach. Tourists will ask you for information, locations, or directions.

CRITICAL RULES:
1. Keep it short: Answer in exactly one brief sentence.
2. No math: NEVER output raw (x, y) coordinates to the user.
3. Speak naturally: Give directions using cardinal directions (North, South, East, West) and reference nearby landmarks (e.g., "Head north toward the boardwalk until you see the yellow building").
4. Formatting: Do not use any punctuation marks in your response.

ENVIRONMENT DATA:
- Grid: 0 to 100 East-West (X), 0 to 100 North-South (Y).
- South (lower Y values): The Shoreline / Ocean.
- North (higher Y values): The Boardwalk.

KEY LOCATIONS:
- Central Pier: (50, 50). The main central landmark.
- Main Lifeguard Tower: (50, 30). Central, red and white.
- Secondary Lifeguard Chair: (80, 20). Eastern section.
- Tuck Shop: (20, 80). Yellow building, northwest.
- First Aid Station: (50, 80). Green building, north central.
- Changing Room & Toilet Block: (20, 85). Blue building, just north of the Tuck Shop.

NAVIGATION PROTOCOL:
When the user asks for directions, look at their provided "current location" and the requested destination. Calculate the direction internally, then translate it into simple walking directions based on the environment data above."""

# --- BUTTON CALLBACK ---
def button_pressed(channel):
    global latest_ai_message, current_x, current_y
    
    print("adjusting for ambient noise")
    with m as source:
        r.adjust_for_ambient_noise(source, duration=2)
        print("You can speak now...")
        latest_ai_message = "Listening..." 
        try:
            audio = r.listen(source, timeout=5)
            print("recognizing speech")
            text = r.recognize_google(audio)
            print(f"you said: {text}")
        except sr.WaitTimeoutError:
            print("Listening timed out.")
            latest_ai_message = "Listening timed out. Please try again."
            threading.Timer(5.0, reset_message).start() 
            return
        except sr.UnknownValueError:
            print("Sorry i could not understand the audio")
            latest_ai_message = "Sorry, I couldn't understand the audio."
            threading.Timer(5.0, reset_message).start() 
            return
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            latest_ai_message = "Network error with speech recognition."
            threading.Timer(5.0, reset_message).start() 
            return
        except KeyboardInterrupt:
            return

    current_location = f"({current_x},{current_y})"    
    user_message = text
    conversation = [
        {
            "role": "user",
            "content": [{"text": system_prompt + " " + user_message + " the current location is " + current_location}],
        }
    ]

    latest_ai_message = "Thinking..."
    
    try:
        response = client.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={"maxTokens": 512, "temperature": 0.5, "topP": 0.9},
        )
        
        response_text = response["output"]["message"]["content"][0]["text"]
        cleaned_text = response_text.replace('(', '').replace('&', 'and').replace('.', "").replace(',', " ")
        print(response_text)
        
        latest_ai_message = cleaned_text
        
        engine.say(cleaned_text)
        engine.runAndWait()

        threading.Timer(10.0, reset_message).start()
        
    except Exception as e:
        print(f"Bedrock Error: {e}")
        latest_ai_message = "Sorry, I had trouble connecting to my brain."
        threading.Timer(5.0, reset_message).start() 


GPIO.add_event_detect(BUTTON_PIN, GPIO.RISING, callback=button_pressed, bouncetime = int(DEBOUNCE_TIME * 1000))

# --- FLASK WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def index():
    # No longer passing coordinates here, the JavaScript will handle it!
    return render_template('index.html')

@app.route('/get_robot_state')
def get_robot_state():
    global latest_ai_message, current_x, current_y
    # Send all the data to the web page at once
    return jsonify({
        "message": latest_ai_message,
        "x": current_x,
        "y": current_y
    })

if __name__ == '__main__':
    try:
        print("Starting Robot Web Server & AI Engine...")
        app.run(host='0.0.0.0', port=5000, use_reloader=False) 
    except KeyboardInterrupt:
        print("\nExiting")
    finally:
        GPIO.cleanup()
