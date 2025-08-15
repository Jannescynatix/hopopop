# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from pymongo import MongoClient

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)

# Einfaches Passwort für das Admin-Panel
ADMIN_PASSWORD = 'mozji7' # ⚠️ ÄNDERE DIESES PASSWORT!

# Globale Variablen für das Modell und den Vektorizer
model = None
vectorizer = None

# MongoDB-Verbindung
MONGO_URI = 'mongodb+srv://wwll:k2AOWvBKW5H5oeZO@py.9gqajwk.mongodb.net/?retryWrites=true&w=majority&appName=py' # ⚠️ HIER URL EINFÜGEN!
client = MongoClient(MONGO_URI)
db = client.ai_text_detector_db
training_data_collection = db.training_data

# Funktion zur initialen Befüllung der Datenbank
def seed_database():
    if training_data_collection.count_documents({}) == 0:
        print("Datenbank ist leer. Befülle sie mit Initialdaten...")
        initial_human_texts = [
            'Als ich gestern Abend durch den Wald spazierte, hörte ich plötzlich ein lautes Knacken hinter mir. Ich drehte mich um, sah aber nichts. Trotzdem beschleunigte ich meine Schritte, denn die Geräusche folgten mir.',
            'Meine Großmutter hat mir ein altes Familienrezept für Apfelkuchen gegeben. Es ist handgeschrieben auf einem zerknitterten Zettel, der Flecken von Zucker und Mehl hat.',
            'Der letzte Roman von Haruki Murakami, den ich gelesen habe, war eine absolute Meisterleistung. Die Charaktere sind so tiefgründig und die Handlung ist surreal und doch so emotional.',
            'Nein ich denke nicht Pascal.',
            'Ich vermute, dass die Wurzel drei ist',
            'Du bist dumm'
        ]
        initial_ki_texts = [
            'Das grundlegende Prinzip der Quantenverschränkung beruht auf der nicht-lokalen Korrelation von Quantenzuständen.',
            'Die Analyse der globalen Wirtschaftsindikatoren zeigt eine deutliche Verschiebung in Richtung digitaler Dienstleistungen.',
            'Ein rekurrierendes neuronales Netzwerk (RNN) ist eine Klasse von künstlichen neuronalen Netzen, die sich durch die Fähigkeit auszeichnen, sequenzielle Daten wie Texte oder Zeitreihen zu verarbeiten.',
            'Das wahrscheinlichste Problem ist, dass dein Modell oder der Vektorizer immer nur ein und dasselbe Ergebnis vorhersagen.',
            'Ja, die Logs zeigen, dass Anfragen an dein Backend gehen, aber etwas stimmt mit der Antwort nicht.',
            'Diese Frage kann ich nicht beantworten.'
        ]

        data_to_insert = [
            {'text': text, 'label': 'menschlich'} for text in initial_human_texts
        ]
        data_to_insert.extend([
            {'text': text, 'label': 'ki'} for text in initial_ki_texts
        ])
        training_data_collection.insert_many(data_to_insert)
        print("Datenbank erfolgreich befüllt.")

# Funktion zum Laden der Daten aus der DB und Trainieren des Modells
def train_and_save_model():
    global model, vectorizer

    # Daten aus der MongoDB-Datenbank laden
    training_data_list = list(training_data_collection.find({}, {'_id': 0}))

    if not training_data_list:
        print("Keine Daten in der Datenbank gefunden. Das Modell kann nicht trainiert werden.")
        model = None
        vectorizer = None
        return

    df = pd.DataFrame(training_data_list)

    # TF-IDF-Vektorizer erstellen
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df['text'])
    y = df['label']

    # Naive Bayes-Modell trainieren
    model = MultinomialNB()
    model.fit(X, y)

    # Modell und Vektorizer als Dateien speichern
    joblib.dump(model, 'model.pkl')
    joblib.dump(vectorizer, 'tokenizer.pkl')

    print("Modell und Vektorizer wurden erfolgreich neu trainiert und gespeichert.")

# Beim Start des Servers initial trainieren
seed_database()
train_and_save_model()


@app.route('/predict', methods=['POST'])
def predict():
    global model, vectorizer
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Kein Text bereitgestellt.'}), 400

    if model is None or vectorizer is None:
        return jsonify({'error': 'Das Modell ist noch nicht geladen oder trainiert.'}), 500

    text_vectorized = vectorizer.transform([text])
    probabilities = model.predict_proba(text_vectorized)[0]
    classes = model.classes_

    mensch_prob = float(probabilities[classes == 'menschlich'])
    ki_prob = float(probabilities[classes == 'ki'])

    return jsonify({
        'menschlich': round(mensch_prob * 100, 2),
        'ki': round(ki_prob * 100, 2)
    })

# NEUER ENDPUNKT: Admin-Login
@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get('password')

    if password == ADMIN_PASSWORD:
        training_data_list = list(training_data_collection.find({}, {'_id': 0}))
        return jsonify({'message': 'Login erfolgreich', 'data': training_data_list})
    else:
        return jsonify({'error': 'Falsches Passwort.'}), 401

# NEUER ENDPUNKT: Daten hinzufügen
@app.route('/add_data', methods=['POST'])
def add_data():
    data = request.json
    text = data.get('text')
    label = data.get('label')
    password = data.get('password')

    if password != ADMIN_PASSWORD:
        return jsonify({'error': 'Falsches Passwort.'}), 401

    if not text or not label:
        return jsonify({'error': 'Text und Label sind erforderlich.'}), 400

    training_data_collection.insert_one({'text': text, 'label': label})
    train_and_save_model()
    return jsonify({'message': 'Daten erfolgreich hinzugefügt und Modell neu trainiert!'})

# NEUER ENDPUNKT: Daten löschen
@app.route('/delete_data', methods=['POST'])
def delete_data():
    data = request.json
    text_to_delete = data.get('text')
    password = data.get('password')

    if password != ADMIN_PASSWORD:
        return jsonify({'error': 'Falsches Passwort.'}), 401

    if not text_to_delete:
        return jsonify({'error': 'Text zum Löschen ist erforderlich.'}), 400

    result = training_data_collection.delete_one({'text': text_to_delete})
    if result.deleted_count > 0:
        train_and_save_model()
        return jsonify({'message': 'Daten erfolgreich gelöscht und Modell neu trainiert!'})
    else:
        return jsonify({'error': 'Text nicht gefunden.'}), 404

if __name__ == '__main__':
    app.run(debug=True)