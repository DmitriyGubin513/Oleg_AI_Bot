from textblob import TextBlob


def analyze_sentiment(text):
    blob = TextBlob(text)

    return blob.sentiment.polarity


user_prompt = input("Чо каво пидор?\n")
polarity = analyze_sentiment(user_prompt)
print(polarity)
