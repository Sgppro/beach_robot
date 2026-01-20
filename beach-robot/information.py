import pyttsx3

import os
import speech_recognition as sr

import json
import boto3

import requests

#text to speech
engine = pyttsx3.init()

engine.setProperty('rate', 150)
engine.setProperty('volume', 1)

# obtain audio from the microphone
r = sr.Recognizer()

#chatbot
client = boto3.client("bedrock-runtime", region_name="ap-southeast-2")

# Set the model ID, e.g., Amazon Nova Lite.
model_id = "amazon.nova-lite-v1:0"

# Start a conversation with the user message.
system_prompt = """You are a robot on a beach, here is the map of the beach. Users will ask you for directions, please give them a concise guide on how to go to certain places.Use the following coordinate map to provide concise, direct instructions to users who ask for the location of facilities. Assume the user's location is known. Provide clear directional vectors.
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
When given the user's current (x, y) coordinates and a destination, calculate the most efficient vector.
Use major landmarks (e.g., "toward the pier," "away from the shoreline," "parallel to the boardwalk") for situational context only if it aids clarity. Do not give coordinate and moving points, assuming each unit length is meter. You are talking to guests, please be using speech that can be easily understood by human.
Please keep your output within 3 sentences, ditch any unnecessary sentence, just give directions and length. For the destination, please refer to the points given in the prompt, do not make up anything"""
 
current_location = "(10,30)"
user_message = "Hi how to go to the changing room"
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
print(response_text)

# while True:
#     print("You can start speaking now")
#     with sr.Microphone() as mic:
#             r.adjust_for_ambient_noise(mic, duration=0.2)
#             audio = r.listen(mic)

#             text = r.recognize_google(audio)
            
#             print(f"Recognized {text}")
