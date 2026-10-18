"""
Lists every text-to-speech voice installed on this Windows machine, with
its index number. Pick a clearer-sounding voice than the robotic default.

Run with: python list_voices.py
"""
import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty("voices")

print(f"Total voices found: {len(voices)}\n")
for i, v in enumerate(voices):
    print(f"[{i}] name={v.name!r}")
    print(f"     id={v.id}")
    print(f"     languages={v.languages}")
    print()

test_index = input("Test karne ke liye index number daalo (ya Enter dabao skip karne ke liye): ").strip()
if test_index.isdigit() and 0 <= int(test_index) < len(voices):
    idx = int(test_index)
    engine.setProperty("voice", voices[idx].id)
    engine.say("Hello, main is voice me bol raha hoon. Time kya hai, chalo test karte hain.")
    engine.runAndWait()