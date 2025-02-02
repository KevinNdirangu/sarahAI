import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import speech_recognition as sr
import json
import requests
from datetime import datetime
import re
import qrcode
import pyttsx3
import os
from spellchecker import SpellChecker
from fuzzywuzzy import fuzz

# File paths
file_name = "response_library.txt"
learned_responses_file = "learned_responses.txt"
notes_file = "assistant_notes.txt"

# API keys and global variables
weather_api_key = "a7ad5b42ed9bd30f62b69b3dd8902481"  # Replace with your Weather Stack API key
response_library = {}
learned_responses = {}

# Text-to-speech engine
engine = pyttsx3.init()

# Functions for managing response and notes files
def load_library():
    try:
        with open(file_name, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_library(library):
    with open(file_name, 'w') as file:
        json.dump(library, file)

def load_responses():
    try:
        with open(learned_responses_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_responses(responses):
    with open(learned_responses_file, 'w') as file:
        json.dump(responses, file)

def load_notes():
    try:
        with open(notes_file, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return ""

def save_note(note):
    with open(notes_file, 'a') as file:
        file.write(f"{note}\n")

response_library = load_library()
learned_responses = load_responses()

def save_response(user_input, assistant_response):
    learned_responses[user_input.lower()] = assistant_response
    save_responses(learned_responses)

# Spell check function to correct typos
def correct_typos(user_input):
    spell = SpellChecker()
    words = user_input.split()
    corrected_words = [spell.correction(word) for word in words]
    return ' '.join(corrected_words)

# Speech recognition
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio).lower()
    except (sr.UnknownValueError, sr.RequestError):
        return input("Type here: ").lower()

# Internet checker
def check_internet():
    try:
        response = requests.get("http://www.google.com", timeout=5)
        return True if response.status_code == 200 else False
    except requests.ConnectionError:
        return False

# Weather API request
def get_weather(city):
    url = f"http://api.weatherstack.com/current?access_key={weather_api_key}&query={city}"
    response = requests.get(url)
    if response.status_code == 200:
        weather_data = response.json()
        try:
            temperature = weather_data['current']['temperature']
            weather_description = weather_data['current']['weather_descriptions'][0]
            return f"Weather in {city}: {temperature}°C, {weather_description}"
        except KeyError:
            return "Failed to fetch weather data - Incorrect API response format"
    else:
        return "Failed to fetch weather data"

# Text-to-Morse converter
MORSE_CODE_DICT = {
    'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.', 'f': '..-.', 'g': '--.',
    'h': '....', 'i': '..', 'j': '.---', 'k': '-.-', 'l': '.-..', 'm': '--', 'n': '-.',
    'o': '---', 'p': '.--.', 'q': '--.-', 'r': '.-.', 's': '...', 't': '-', 'u': '..-',
    'v': '...-', 'w': '.--', 'x': '-..-', 'y': '-.--', 'z': '--..', '1': '.----',
    '2': '..---', '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', '0': '-----'
}

def text_to_morse(text):
    return ' '.join(MORSE_CODE_DICT.get(char, char) for char in text.lower())

# QR Code generation
def generate_qr_code(data):
    qr = qrcode.make(data)
    qr.show()

# Recognize user intent with fuzzy matching
def recognize_intent(user_input):
    weather_keywords = ["weather", "climate", "forecast"]
    time_keywords = ["time", "clock"]
    date_keywords = ["date", "day"]
    morse_keywords = ["morse", "code"]
    qr_code_keywords = ["qr", "code"]
    note_keywords = ["note", "remember"]

    if any(keyword in user_input for keyword in weather_keywords):
        return "weather"
    elif any(keyword in user_input for keyword in time_keywords):
        return "time"
    elif any(keyword in user_input for keyword in date_keywords):
        return "date"
    elif any(keyword in user_input for keyword in morse_keywords):
        return "morse"
    elif any(keyword in user_input for keyword in qr_code_keywords):
        return "qr_code"
    elif any(keyword in user_input for keyword in note_keywords):
        return "note"
    
    return "unknown"

# Process user input
def process_input(user_input):
    # Correct typos before processing
    user_input_corrected = correct_typos(user_input)
    
    # If the corrected input is significantly different from the original, ask for confirmation
    if fuzz.ratio(user_input, user_input_corrected) < 80:  # Adjust threshold for typo detection
        user_input = confirm_typo(user_input, user_input_corrected)
    
    if "exit" in user_input:
        return True
    
    response_text.insert(tk.END, "Assistant: Thinking...\n\n")
    response_text.see(tk.END)
    
    intent = recognize_intent(user_input)
    response = ""
    
    if intent == "weather":
        city = re.search(r"in (\w+(\s\w+)?)", user_input)
        if city:
            city = city.group(1)
            response = get_weather(city)
        else:
            response = "Please specify the city for the weather."
    elif intent == "time":
        response = f"Current time is {datetime.now().time()}"
    elif intent == "date":
        response = f"Today's date is {datetime.now().date()}"
    elif intent == "morse":
        text = re.search(r"translate (.+) to morse code", user_input)
        if text:
            text = text.group(1)
            response = text_to_morse(text)
    elif intent == "qr_code":
        data = re.search(r"generate qr code for (.+)", user_input)
        if data:
            data = data.group(1)
            generate_qr_code(data)
            response = "QR code generated and displayed."
    elif intent == "note":
        note = re.search(r"(take|save) a note (.+)", user_input)
        if note:
            note = note.group(2)
            save_note(note)
            response = "Note saved successfully."
    else:
        if user_input in learned_responses:
            response = learned_responses[user_input]
        else:
            if user_input in response_library:
                response = response_library[user_input]
            else:
                response = "I'm not sure how to respond to that."
                new_response = input("Please teach me, how should I respond to that?\n")
                response_library[user_input] = new_response
                save_library(response_library)
                save_response(user_input, new_response)
                response = "Thanks for teaching me!"

    engine.say(response)
    engine.runAndWait()
    response_text.insert(tk.END, f"Assistant: {response}\n\n")
    response_text.see(tk.END)
    return False

# GUI setup
def on_click():
    user_input = entry.get()
    should_exit = process_input(user_input)
    if should_exit:
        root.quit()

def on_enter(event):
    on_click()

root = tk.Tk()
root.title("Virtual Assistant")

frame = tk.Frame(root)
frame.pack(pady=10)

entry = tk.Entry(frame, width=50)
entry.grid(row=0, column=0, padx=10)
entry.bind('<Return>', on_enter)

send_button = tk.Button(frame, text="Send", command=on_click)
send_button.grid(row=0, column=1)

response_text = scrolledtext.ScrolledText(root, height=15, width=80)
response_text.pack(padx=10, pady=10)

root.mainloop()
