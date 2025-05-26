from typing import Text, Dict, Any, List

import datetime
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from spacy.lang.en.tokenizer_exceptions import morph

from config import weather_APIKEY
import spacy

nlp = spacy.load("ru_core_news_sm")


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
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_APIKEY}&units=metric&lang=ru"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            temp = data["main"]["temp"]
            weather_desc = data["weather"][0]["description"]
            return f"В городе {city} сейчас {weather_desc}. Температура {temp}°C."
        else:
            return "Не удалось получить информацию о погоде. Попробуйте другой город."
    except Exception as e:
        return f"Произошла Ошибка: {e}"


class ActionGetWeather(Action):
    def name(self) -> Text:
        return "action_get_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        city = tracker.get_slot("city")

        if not city:
            text = tracker.latest_message.get("text")
            doc = nlp(text)
            city = next((ent.text for ent in doc.ents if ent.label_ == "GPE"), None)

        city_norm = city

        if not city_norm:
            dispatcher.utter_message(text="уточните город в вашем запросе")
            return []

        response = get_weather(city_norm)

        dispatcher.utter_message(text=response)
        return [SlotSet("city", city_norm)]



#Дата, время и день недели
class ActionTellTime(Action):
    def name(self) -> Text:
        return "action_tell_time"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        time_format = domain.get("config", {}).get("time_format", "%H:%M")
        now = datetime.datetime.now().strftime(time_format)
        message = f"Сейчас {now}"
        dispatcher.utter_message(text=message)
        return []


class ActionTellDay(Action):
    def name(self) -> Text:
        return "action_tell_day"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        lang = domain.get("config", {}).get("language", "ru")
        day = datetime.datetime.now().strftime("%A")

        days_translation = {
            "ru": {
                "Monday": "Понедельник",
                "Tuesday": "Вторник",
                "Wednesday": "Среда",
                "Thursday": "Четверг",
                "Friday": "Пятница",
                "Saturday": "Суббота",
                "Sunday": "Воскресенье"
            },
            "en": {
                "Monday": "Monday",
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
                "Friday": "Friday",
                "Saturday": "Saturday",
                "Sunday": "Sunday"
            }
        }

        day_localized = days_translation.get(lang, {}).get(day, day)
        message = f"Сегодня {day_localized}"
        dispatcher.utter_message(text=message)
        return []

class ActionTellDate(Action):
    def name(self) -> Text:
        return "action_tell_date"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        lang = domain.get("config", {}).get("language", "ru")
        date_format = "%d.%m.%Y" if lang == "ru" else "%Y-%m-%d"
        date = datetime.datetime.now().strftime(date_format)
        message = f"Сегодня {date}"
        dispatcher.utter_message(text=message)
        return []