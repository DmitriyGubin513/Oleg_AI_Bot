import spacy

nlp = spacy.load("ru_core_news_sm")


if __name__ == "__main__":
    text = input("Что на уме?\n")
    doc = nlp(text)
    ents = [(ent.text, ent.label_) for ent in doc.ents]
    print(f"Сущности в сообщении: {ents}")
