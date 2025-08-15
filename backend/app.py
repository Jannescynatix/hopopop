from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline

app = Flask(__name__)
CORS(app)

DATA_FILE = 'data.json'
MODEL_FILE = 'model_pipeline.pkl'

# --- Hilfsfunktionen für Daten und Modell ---

def load_data():
    """Lade Trainingsdaten aus der JSON-Datei."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"menschlich": [], "ki": []}

def save_data(data):
    """Speichere Trainingsdaten in der JSON-Datei."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def train_and_save_model():
    """Trainiere das Modell neu und speichere es."""
    data = load_data()
    human_texts = data['menschlich']
    ki_texts = data['ki']

    if not human_texts or not ki_texts:
        return False # Nicht genügend Daten zum Trainieren

    df_ki = pd.DataFrame({'text': ki_texts, 'label': 'ki'})
    df_human = pd.DataFrame({'text': human_texts, 'label': 'menschlich'})
    df = pd.concat([df_ki, df_human], ignore_index=True)

    pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer()),
        ('classifier', SGDClassifier(loss='log_loss', random_state=42))
    ])
    pipeline.fit(df['text'], df['label'])
    joblib.dump(pipeline, MODEL_FILE)
    return True

# Lade das Modell beim Start der App
try:
    pipeline = joblib.load(MODEL_FILE)
except FileNotFoundError:
    print("Modell-Datei nicht gefunden. Trainiere ein neues Modell...")
    if not train_and_save_model():
        print("Konnte kein Modell trainieren: Nicht genügend Daten. Bitte fügen Sie Trainingsdaten hinzu.")
    pipeline = joblib.load(MODEL_FILE)


# --- API-Endpunkte ---

@app.route('/predict', methods=['POST'])
def predict():
    """Analysiere einen Text auf KI-Wahrscheinlichkeit."""
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Kein Text bereitgestellt.'}), 400

    try:
        probabilities = pipeline.predict_proba([text])[0]
        classes = pipeline.classes_

        mensch_prob = float(probabilities[classes == 'menschlich'])
        ki_prob = float(probabilities[classes == 'ki'])

        return jsonify({
            'menschlich': round(mensch_prob * 100, 2),
            'ki': round(ki_prob * 100, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/data', methods=['GET'])
def get_data():
    """Gibt die aktuellen Trainingsdaten zurück."""
    return jsonify(load_data())


@app.route('/add_text', methods=['POST'])
def add_text():
    """Fügt einen Text hinzu und trainiert das Modell neu."""
    data = request.json
    text = data.get('text', '').strip()
    label = data.get('label', '')

    if not text or label not in ['menschlich', 'ki']:
        return jsonify({'error': 'Ungültige Eingabe.'}), 400

    training_data = load_data()
    training_data[label].append(text)
    save_data(training_data)

    if train_and_save_model():
        global pipeline
        pipeline = joblib.load(MODEL_FILE)
        return jsonify({'message': 'Text hinzugefügt und Modell neu trainiert.'})
    else:
        return jsonify({'message': 'Text hinzugefügt, aber nicht genügend Daten zum Trainieren.'})


@app.route('/delete_text', methods=['POST'])
def delete_text():
    """Löscht einen Text und trainiert das Modell neu."""
    data = request.json
    text_to_delete = data.get('text', '').strip()
    label = data.get('label', '')

    training_data = load_data()

    if text_to_delete in training_data[label]:
        training_data[label].remove(text_to_delete)
        save_data(training_data)

        if train_and_save_model():
            global pipeline
            pipeline = joblib.load(MODEL_FILE)
            return jsonify({'message': 'Text gelöscht und Modell neu trainiert.'})
        else:
            return jsonify({'message': 'Text gelöscht, aber nicht genügend Daten zum Trainieren.'})

    return jsonify({'error': 'Text nicht gefunden.'}), 404


if __name__ == '__main__':
    app.run(debug=True)