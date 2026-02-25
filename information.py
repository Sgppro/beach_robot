import pyttsx3

import os
import speech_recognition as sr

import json
import boto3

import requests


os.environ['ALSA_CARD'] = '2'
#text to speech
engine = pyttsx3.init()

engine.setProperty('rate', 120)
engine.setProperty('volume', 1)

# obtain audio from the microphone
r = sr.Recognizer()
m = sr.Microphone()

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



client = boto3.client("bedrock-runtime", region_name="ap-southeast-2")

# Set the model ID, e.g., Amazon Nova Lite.
model_id = "amazon.nova-lite-v1:0"

# Start a conversation with the user message.
system_prompt = """You are a robot on a beach, here is some key locations of the beach, tourist will ask you question and please answer them within a sentence, if they ask for direction, do not give them coordinate but instead refer to directions such as north, and landmarks such as torwards sth sth. Do not add any punctation mark in the response
Beach Map & Coordinates:
Orientation: Rectangular grid, 0 to 100 points East-West (x) and North-South (y).
Shoreline: Southern boundary (lower y-values).
Boardwalk: Northern boundary (higher y-values).
Central Pier: Landmark at coordinates (50, 50).
Key Locations:
Main Lifeguard Tower: (50, 30). Central, red and white.
Secondary Lifeguard Chair: (80, 20). Eastern section.
Tuck Shop: (20, 80). Yellow building, northwest.
First Aid Station: (50, 80). Green building, north central.
Changing Room & Toilet Block: (20, 85). Blue building, just north of Tuck Shop.
Navigation Protocol:
When given the user's current (x, y) coordinates and a destination, calculate the most efficient vector."""
 
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
print("a")
