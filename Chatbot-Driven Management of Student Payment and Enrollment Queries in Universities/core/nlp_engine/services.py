import joblib
import pandas as pd
import random
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(BASE_DIR, "nlp_engine", "model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "nlp_engine", "vectorizer.pkl")
DATA_PATH = os.path.join(BASE_DIR, "dataset", "intents.csv")

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)
data = pd.read_csv(DATA_PATH)

def generate_response(text):
    X = vectorizer.transform([text])
    intent = model.predict(X)[0]

    responses = data[data["intent"] == intent]["response"].tolist()
    return random.choice(responses)
