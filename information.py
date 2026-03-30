import RPi.GPIO as GPIO
import time

import pyttsx3

import os
import speech_recognition as sr

import json
import boto3

import requests

BUTTON_PIN = 26 
DEBOUNCE_TIME = 0.2

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN)

os.environ['ALSA_CARD'] = '2'
#text to speech
engine = pyttsx3.init()

engine.setProperty('rate', 120)
engine.setProperty('volume', 1)

# obtain audio from the microphone
r = sr.Recognizer()
m = sr.Microphone()


client = boto3.client("bedrock-runtime", region_name="ap-southeast-2")


# Set the model ID, e.g., Amazon Nova Lite.
model_id = "amazon.nova-lite-v1:0"

# Start a conversation with the user message.
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


def button_pressed(channel):
    print("adjusting for ambient noise")
    with m as source:
        r.adjust_for_ambient_noise(source, duration=2)
        print("You can speak now...")
        audio = r.listen(source)
    
    print("recognizing specch")
    try:
        text = r.recognize_google(audio)
        print(f"you said: {text}")
    except sr.UnknownValueError:
        print("Sorry i could not understand the audio")
        text = ""
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        text = ""
    except KeyboardInterrupt:
        print("Keyboard has interrupted")
        text  = ""

    current_location = "(10,30)"    
    user_message = text
    conversation = [
        {
            "role": "user",
            "content": [{"text": system_prompt+user_message+"the current location is"+current_location}],
        }
    ]


    # Send the message to the model, using a basic inference configuration.
    response = client.converse(
        modelId=model_id,
        messages=conversation,
        inferenceConfig={"maxTokens": 512, "temperature": 0.5, "topP": 0.9},
    )
    
    # Extract and print the response text.
    response_text = response["output"]["message"]["content"][0]["text"]
    cleaned_text = response_text.replace('(', '').replace('&', 'and').replace('.', "").replace(',', " ")
    print(response_text)
    print(cleaned_text)
    
    engine.say(cleaned_text)
    engine.runAndWait()
    
    


GPIO.add_event_detect(BUTTON_PIN, GPIO.RISING, callback=button_pressed, bouncetime = int(DEBOUNCE_TIME * 1000))

button_pressed("a")

try:
    print("script running")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting")
finally:
    GPIO.cleanup()
