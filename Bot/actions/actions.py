from typing import Text, Dict, Any, List

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from spacy.lang.en.tokenizer_exceptions import morph

from config import weather_APIKEY
from ents.main import nlp


# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa-pro/concepts/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_APIKEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        temp = data["main"]["temp"]
        weather_desc = data["weather"][0]["description"]
        return f"В городе {city} сейчас {weather_desc} при температуре {temp}°C."
    else:
        return "Не удалось получить информацию о погоде. Попробуйте другой город."


class ActionGetWeather(Action):
    def name(self) -> Text:
        return "utter_get_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        city = tracker.get_slot("city")

        if not city:
            text = tracker.latest_message.get("text")
            doc = nlp(text)
            city = next((ent.text for ent in doc.ents if ent.label_ == "GPE"), None)

        city_norm = morph.parse(city)[0].normal_form if city else None

        if not city_norm:
            dispatcher.utter_message(response="utter_ask_city")
            return []

        response = get_weather(city_norm)

        dispatcher.utter_message(text=response)
        return [SlotSet("last_bot_message", response)]
