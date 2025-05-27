import sqlite3
from typing import Text, Dict, Any, List
import datetime
import requests
import re
import ast
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import spacy
from duckduckgo_search.duckduckgo_search import DDGS

from config import weather_APIKEY

DB_NAME = "bot.db"

nlp = spacy.load("ru_core_news_sm")


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
            return f"Мой синоптик не знает о городе {city}, пожалуйста попробуйте другой город, сэр."
    except Exception as e:
        return f"Что-то пошло не так ({e}), пожалуйста повторите, сэр."


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_memory (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        favorite_topic TEXT,
        last_seen TEXT
    );
    """)
    conn.commit()
    conn.close()


class ActionGetWeather(Action):
    def name(self) -> Text:
        return "action_get_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text = tracker.latest_message.get("text", "")
        doc = nlp(text)

        ent = next((e for e in doc.ents if e.label_ == "LOC"), None)
        if ent:
            lemmas = [token.lemma_ for token in ent]
            city = " ".join(lemma.title() for lemma in lemmas)
        else:
            city = tracker.get_slot("city")

        if not city:
            dispatcher.utter_message(template="utter_ask_city")
            return []

        response = get_weather(city)

        dispatcher.utter_message(text=response)
        return [SlotSet("city", city)]


# Дата, время и день недели
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


# Калькуляция
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
            return []

        try:
            result = self._safe_calculation(math_expr)
            msg = self._format_result(result, lang)
        except:
            msg = self._get_message("invalid", lang)

        dispatcher.utter_message(text=msg)
        return []

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


class ActionRepeat(Action):
    """Используем регулярные выражения, чтобы разбирать пользовательский ввод
    формата 'Скажи кот', 'Повтори: собакен', 'Пожалуйста повтори 'Уточка'' и
    возвращать пользователю фразу без просьбы повторить :3
    """

    def name(self) -> Text:
        return "action_repeat"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        try:
            user_msg = tracker.latest_message.get("text", "") or ""

            verbs = ["повтори", "скажи"]
            postfixes = ["за мной", "пожалуйста"]

            verbs_pattern = "|".join(re.escape(a) for a in verbs)
            postfixes_pattern = "|".join(re.escape(a) for a in postfixes)

            # финальный шаблон
            pattern = re.compile(
                rf'''
                ^                                   # начало строки
                (?:.*?\b)?                          # любой ввод перед ключевыми словами: "повтори" или "скажи" 
                                                    # (напр., "пожалуйста скажи")
                (?:{verbs_pattern})                 # ключевые слова
                (?:\s+(?:{postfixes_pattern}))?     # необязательное "за мной"
                (?:[:\s]+)                          # разделитель: двоеточие или пробельчики
                [«"”]?                              # необязательная открывающая кавычка
                (?P<text_to_repeat>.+?)             # фраза для повторения (извлекаем -> group 'text_to_repeat')
                [»"”]?                              # необязательная закрывающая кавычка
                $                                   # конец строки
                ''',
                flags=re.IGNORECASE | re.UNICODE | re.VERBOSE
            )

            match = pattern.match(user_msg)
            if match:
                to_repeat = match.group("text_to_repeat").strip()
                dispatcher.utter_message(text=f"Повторяю: {to_repeat}")
            else:
                dispatcher.utter_message(
                    text="Не понял, что повторить. Скажите, например, 'Пожалуйста повтори: кот' -> 'кот' "
                         "или 'Скажи за мной Привет' -> 'Привет'"
                )
            return []
        except Exception as e:
            dispatcher.utter_message(
                text=f"Что-то пошло не так ({e}), пожалуйста повторите, сэр."
            )
            return []


class ActionSaveName(Action):
    def name(self):
        return "action_save_name"

    def run(self, dispatcher, tracker: Tracker, domain):
        try:
            init_db()
            user_id = tracker.sender_id
            name = tracker.get_slot("name")
            topic = tracker.get_slot("favorite_topic")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memory(user_id, name, favorite_topic, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  name=excluded.name,
                  favorite_topic=excluded.favorite_topic,
                  last_seen=excluded.last_seen
            """, (user_id, name, topic, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()

            dispatcher.utter_message(text=f"Приятно познакомиться, {name}")
            return []
        except Exception as e:
            dispatcher.utter_message(text=f"Память меня подводит ({e}) :с")
            return []


class ActionSaveTopic(Action):
    def name(self):
        return "action_save_topic"

    def run(self, dispatcher, tracker: Tracker, domain):
        try:
            init_db()
            user_id = tracker.sender_id
            name = tracker.get_slot("name")
            topic = tracker.get_slot("favorite_topic")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memory(user_id, name, favorite_topic, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  name=excluded.name,
                  favorite_topic=excluded.favorite_topic,
                  last_seen=excluded.last_seen
            """, (user_id, name, topic, datetime.datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()

            dispatcher.utter_message(text=f"Очень здорово, что тебе интересно {topic}.")
            return []
        except Exception as e:
            dispatcher.utter_message(text=f"Память меня подводит ({e}) :с")
            return []


class ActionAskAboutSelf(Action):
    def name(self):
        return "action_ask_about_self"

    def run(self, dispatcher, tracker: Tracker, domain):
        try:
            init_db()
            user_id = tracker.sender_id

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name, favorite_topic FROM user_memory WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                name, topic = row
                if name and topic:
                    text = f"Тебя зовут {name}, и тебе интересно {topic}."
                elif name and not topic:
                    text = f"Тебя зовут {name}! Расскажи, что тебе интересно?"
                elif topic and not name:
                    text = f"Тебе интересно {topic}, расскажи, пожалуйста, как тебя зовут?"
                else:
                    text = ("Я ничего о тебе не знаю о.о\n"
                            "Расскажи, как тебя зовут и что тебе интересно?")

                dispatcher.utter_message(text=text)
                return [SlotSet("name", name), SlotSet("favorite_topic", topic)]
            else:
                dispatcher.utter_message(text=("Я ничего о тебе не знаю о.о\n"
                                               "Расскажи, как тебя зовут и что тебе интересно?"))
            return []
        except Exception as e:
            dispatcher.utter_message(text=f"Память меня подводит ({e}) :с")
            return []


class ActionMemoryInit(Action):
    def name(self):
        return "action_memory_init"

    def run(self, dispatcher, tracker: Tracker, domain):
        try:
            init_db()
            user_id = tracker.sender_id

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name, favorite_topic FROM user_memory WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()

            to_save = []
            if row:
                name, topic = row
                if name:
                    to_save.append(SlotSet("name", name))
                    dispatcher.utter_message(f"Привет, {name}.")
                if topic:
                    to_save.append(SlotSet("favorite_topic", topic))

                return to_save
            return []
        except Exception as e:
            return []


class ActionSearchWeb(Action):
    def name(self):
        return "action_search_web"

    def run(self, dispatcher, tracker, domain):
        term = tracker.get_slot("search_term")
        if not term:
            dispatcher.utter_message("Я не понял, что нужно найти. Пожалуйста повторите.")
            return []

        with DDGS() as ddgs:
            results = ddgs.text(term, max_results=5)

        if not results:
            dispatcher.utter_message(text=f"Ничего не нашлось по запросу '{term}'")
            return []

        reply = ["Вот, что мне удалось найти:"]
        for r in results:
            title = r.get("title") or r.get("body","(без заголовка)")
            url = r.get("href") or r.get("url","--")
            reply.append(f"- {title}: {url}")

        dispatcher.utter_message(text="\n".join(reply))
        return [SlotSet("search_term", term)]
