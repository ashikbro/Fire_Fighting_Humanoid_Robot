import pyttsx3

def voice_alert(message):
    engine = pyttsx3.init()
    engine.say(message)
    engine.runAndWait()

if __name__ == "__main__":
    test_message = "Warning! Fire severity is high. Please take immediate action."
    voice_alert(test_message)
