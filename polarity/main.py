from textblob import TextBlob
from googletrans import Translator
from langdetect import detect

translator = Translator()


def is_english(text):
    return detect(text) == 'en'


def to_english(text):
    return translator.translate(text, dest='en').text


def analyze_sentiment(text):
    blob = TextBlob(text)

    return blob.sentiment.polarity


while True:
    user_prompt = input("Привет, чем могу помочь?\n")
    if not is_english(user_prompt):
        user_prompt = to_english(user_prompt)
    polarity = analyze_sentiment(user_prompt)
    if polarity < 0:
        print("А вы хороший человек!")
    elif polarity > 0:
        print("А вы отвратительны, сударь...")
    else:
        print("Вы нейтральны :3")
