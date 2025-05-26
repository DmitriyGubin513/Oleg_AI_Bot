from typing import Text, Dict, Any, List

import datetime
import requests
import re
import ast
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

#Калькуляция
class ActionCalculate(Action):
    def name(self) -> Text:
        return "action_calculate"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        lang = domain.get("config", {}).get("language", "ru")
        user_text = tracker.latest_message.get("text", "")

        math_expr = self._extract_math_expression(user_text)

        if not math_expr:
            msg = self._get_message("no_expr", lang)
            dispatcher.utter_message(text=msg)
            return [SlotSet("last_bot_message", msg)]

        try:
            result = self._safe_calculation(math_expr)
            msg = self._format_result(result, lang)
        except:
            msg = self._get_message("invalid", lang)

        dispatcher.utter_message(text=msg)
        return [SlotSet("last_bot_message", msg)]

    def _extract_math_expression(self, text: Text) -> Text:
        """Поиск математических выражений с улучшенным regex"""
        matches = re.findall(r"(?:\d+\.?\d*|\.\d+|\d+)(?:\s*[+\-*/%]\s*(?:\d+\.?\d*|\.\d+|\d+)|\([^)]+\))+", text)
        return matches[0] if matches else ""

    def _safe_calculation(self, expr: Text) -> float:
        """Безопасное вычисление с проверкой AST"""
        tree = ast.parse(expr, mode='eval')

        allowed_nodes = (
            ast.Expression, ast.Constant, ast.BinOp,
            ast.UnaryOp, ast.Add, ast.Sub,
            ast.Mult, ast.Div, ast.USub, ast.UAdd
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError("Недопустимая операция")

        return eval(expr)

    def _format_result(self, value: float, lang: Text) -> Text:
        """Форматирование результата с учетом языка"""
        if lang == "ru":
            return f"📊 Результат: {value:.2f}".replace(".00", "")  # Убираем .00 для целых чисел
        return f"📊 Result: {value:.2f}".replace(".00", "")

    def _get_message(self, msg_type: Text, lang: Text) -> Text:
        """Локализованные сообщения (сохранена оригинальная логика)"""
        messages = {
            "ru": {
                "no_expr": "🔢 Не вижу математического выражения",
                "invalid": "❌ Не могу вычислить это выражение"
            },
            "en": {
                "no_expr": "🔢 I can't find a math expression",
                "invalid": "❌ Can't calculate this expression"
            }
        }
        return messages.get(lang, {}).get(msg_type, "")