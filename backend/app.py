# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from pymongo import MongoClient
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)

# Passwort für das Admin-Panel
ADMIN_PASSWORD = 'mozji7' # ⚠️ ÄNDERE DIESES PASSWORT!

# Globale Variablen für das Modell und den Vektorizer
model = None

# MongoDB-Verbindung
MONGO_URI = 'mongodb+srv://wwll:k2AOWvBKW5H5oeZO@py.9gqajwk.mongodb.net/?retryWrites=true&w=majority&appName=py' # ⚠️ HIER URL EINFÜGEN!
client = MongoClient(MONGO_URI)
db = client.ai_text_detector_db
training_data_collection = db.training_data

# --- Feature Engineering: Benutzerdefinierte Transformer ---

class TextFeaturesExtractor(BaseEstimator, TransformerMixin):
    """
    Extrahiert numerische Features aus Texten (z.B. Wortanzahl, Satzanzahl).
    """
    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        num_sentences = X.apply(lambda text: len(re.split('[.!?]', text)))
        num_words = X.apply(lambda text: len(text.split()))
        avg_word_length = X.apply(lambda text: sum(len(word) for word in text.split()) / len(text.split()) if len(text.split()) > 0 else 0)

        return pd.DataFrame({
            'num_sentences': num_sentences,
            'num_words': num_words,
            'avg_word_length': avg_word_length
        })

# --- Daten- und Modell-Logik ---

def seed_database():
    """Befüllt die Datenbank nur, wenn sie leer ist."""
    print("[LOG] Überprüfe Datenbank...")
    if training_data_collection.count_documents({}) == 0:
        print("[LOG] Datenbank ist leer. Befülle sie mit Initialdaten...")
        initial_human_texts = [
            'Als ich gestern Abend durch den Wald spazierte, hörte ich plötzlich ein lautes Knacken hinter mir. Ich drehte mich um, sah aber nichts. Trotzdem beschleunigte ich meine Schritte, denn die Geräusche folgten mir.',
            'Meine Großmutter hat mir ein altes Familienrezept für Apfelkuchen gegeben. Es ist handgeschrieben auf einem zerknitterten Zettel, der Flecken von Zucker und Mehl hat.',
            'Der letzte Roman von Haruki Murakami, den ich gelesen habe, war eine absolute Meisterleistung. Die Charaktere sind so tiefgründig und die Handlung ist surreal und doch so emotional.',
            'Nein ich denke nicht Pascal.',
            'Ich vermute, dass die Wurzel drei ist',
            'Du bist dumm',
            'Heute ist das Wetter wirklich schön, die Sonne scheint und es ist warm. Ich werde den Nachmittag im Park verbringen und ein Buch lesen.',
            'Der Verkehr in der Stadt war heute eine Katastrophe. Ich habe fast eine Stunde gebraucht, um zur Arbeit zu kommen.',
            'Mein Lieblingsessen ist Pizza mit extra Käse. Ich könnte sie jeden Tag essen, ohne dass sie mir über wird.',
            'Das Konzert gestern war unglaublich! Die Band hat eine so tolle Energie auf die Bühne gebracht.',
        ]
        initial_ki_texts = [
            'Das grundlegende Prinzip der Quantenverschränkung beruht auf der nicht-lokalen Korrelation von Quantenzuständen.',
            'Die Analyse der globalen Wirtschaftsindikatoren zeigt eine deutliche Verschiebung in Richtung digitaler Dienstleistungen.',
            'Ein rekurrierendes neuronales Netzwerk (RNN) ist eine Klasse von künstlichen neuronalen Netzen, die sich durch die Fähigkeit auszeichnen, sequenzielle Daten wie Texte oder Zeitreihen zu verarbeiten.',
            'Das wahrscheinlichste Problem ist, dass dein Modell oder der Vektorizer immer nur ein und dasselbe Ergebnis vorhersagen.',
            'Ja, die Logs zeigen, dass Anfragen an dein Backend gehen, aber etwas stimmt mit der Antwort nicht.',
            'Diese Frage kann ich nicht beantworten.',
            'Die Entwicklung nachhaltiger Energiesysteme erfordert die Integration erneuerbarer Quellen und eine effiziente Speicherung der erzeugten Energie.',
            'In der modernen Linguistik wird der Begriff "Diskursanalyse" zur Untersuchung der sprachlichen Interaktion in ihrem sozialen Kontext verwendet.',
            'Die Bedeutung des Internets der Dinge (IoT) wächst exponentiell, da immer mehr Geräte vernetzt werden und Daten austauschen.',
            'Maschinelles Lernen bietet vielversprechende Ansätze zur Optimierung logistischer Prozesse und zur Vorhersage von Markttrends.'
        ]

        data_to_insert = [
            {'text': text, 'label': 'menschlich', 'trained': True} for text in initial_human_texts
        ]
        data_to_insert.extend([
            {'text': text, 'label': 'ki', 'trained': True} for text in initial_ki_texts
        ])
        training_data_collection.insert_many(data_to_insert)
        print("[LOG] Datenbank erfolgreich befüllt.")
    else:
        print("[LOG] Datenbank enthält bereits Daten. Überspringe Befüllung.")

def train_and_save_model():
    """Lädt die Daten aus der DB und trainiert das Modell neu."""
    global model
    print("[LOG] Starte Modell-Training...")

    try:
        training_data_list = list(training_data_collection.find({'trained': True}, {'_id': 0}))

        if not training_data_list:
            print("[LOG] Keine trainierbaren Daten in der Datenbank gefunden.")
            model = None
            return

        df = pd.DataFrame(training_data_list)
        print(f"[LOG] {len(df)} Datensätze für das Training geladen.")

        preprocessor = ColumnTransformer(
            transformers=[
                ('text_tfidf', TfidfVectorizer(ngram_range=(1, 3), max_features=1000), 'text'),
                ('text_features', TextFeaturesExtractor(), 'text')
            ],
            remainder='passthrough'
        )

        model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', MultinomialNB())
        ])

        X = df[['text']]
        y = df['label']

        model.fit(X, y)

        joblib.dump(model, 'model_pipeline.pkl')
        print("[LOG] Modell-Pipeline wurde erfolgreich neu trainiert und gespeichert.")

        training_data_collection.update_many({'trained': False}, {'$set': {'trained': True}})
        print("[LOG] Alle neuen Daten als 'trained' markiert.")
        print("[STATUS] TRAINING ABGESCHLOSSEN.")

    except Exception as e:
        print(f"[FEHLER] Fehler beim Neu-Trainieren des Modells: {str(e)}")
        # Optional: Sende eine E-Mail oder eine andere Benachrichtigung an den Administrator
        # return jsonify({'error': f'Ein interner Fehler ist aufgetreten: {str(e)}'}), 500

# Beim Start des Servers initial trainieren
seed_database()
train_and_save_model()

# --- API Endpunkte ---

@app.route('/predict', methods=['POST'])
def predict():
    global model
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Kein Text bereitgestellt.'}), 400

    if model is None:
        print("[FEHLER] Vorhersage fehlgeschlagen: Modell ist nicht geladen oder trainiert.")
        return jsonify({'error': 'Das Modell ist noch nicht geladen oder trainiert.'}), 500

    try:
        text_df = pd.DataFrame([{'text': text}])
        probabilities = model.predict_proba(text_df)[0]
        classes = model.classes_

        mensch_prob = float(probabilities[classes == 'menschlich'])
        ki_prob = float(probabilities[classes == 'ki'])

        print(f"[LOG] Vorhersage für Text: '{text[:30]}...'. Ergebnis: Menschlich: {round(mensch_prob * 100, 2)}%, KI: {round(ki_prob * 100, 2)}%")

        return jsonify({
            'menschlich': round(mensch_prob * 100, 2),
            'ki': round(ki_prob * 100, 2)
        })
    except Exception as e:
        print(f"[FEHLER] Vorhersage konnte nicht durchgeführt werden: {str(e)}")
        return jsonify({'error': 'Ein Fehler bei der Vorhersage ist aufgetreten.'}), 500


@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get('password')

    if password == ADMIN_PASSWORD:
        print("[LOG] Admin-Login erfolgreich.")
        training_data_list = list(training_data_collection.find({}, {'_id': 0}))
        return jsonify({'message': 'Login erfolgreich', 'data': training_data_list})
    else:
        print("[FEHLER] Admin-Login fehlgeschlagen: Falsches Passwort.")
        return jsonify({'error': 'Falsches Passwort.'}), 401

@app.route('/add_data', methods=['POST'])
def add_data():
    data = request.json
    text = data.get('text')
    label = data.get('label')
    password = data.get('password')

    if password != ADMIN_PASSWORD:
        print("[FEHLER] Daten hinzufügen fehlgeschlagen: Falsches Passwort.")
        return jsonify({'error': 'Falsches Passwort.'}), 401

    if not text or not label:
        print("[FEHLER] Daten hinzufügen fehlgeschlagen: Text und Label fehlen.")
        return jsonify({'error': 'Text und Label sind erforderlich.'}), 400

    training_data_collection.insert_one({'text': text, 'label': label, 'trained': False})
    print(f"[LOG] Neuer Datensatz ({label}) zur Warteschlange hinzugefügt: '{text[:30]}...'")

    return jsonify({'message': 'Daten erfolgreich zur Trainingswarteschlange hinzugefügt!'})

@app.route('/delete_data', methods=['POST'])
def delete_data():
    data = request.json
    text_to_delete = data.get('text')
    password = data.get('password')

    if password != ADMIN_PASSWORD:
        print("[FEHLER] Daten löschen fehlgeschlagen: Falsches Passwort.")
        return jsonify({'error': 'Falsches Passwort.'}), 401

    if not text_to_delete:
        print("[FEHLER] Daten löschen fehlgeschlagen: Text zum Löschen fehlt.")
        return jsonify({'error': 'Text zum Löschen ist erforderlich.'}), 400

    result = training_data_collection.delete_one({'text': text_to_delete})
    if result.deleted_count > 0:
        print(f"[LOG] Datensatz erfolgreich gelöscht: '{text_to_delete[:30]}...'")
        return jsonify({'message': 'Daten erfolgreich gelöscht.'})
    else:
        print("[FEHLER] Daten löschen fehlgeschlagen: Text nicht in der DB gefunden.")
        return jsonify({'error': 'Text nicht gefunden.'}), 404

# NEUER ENDPUNKT: Modell neu trainieren
@app.route('/retrain_model', methods=['POST'])
def retrain_model():
    data = request.json
    password = data.get('password')

    if password != ADMIN_PASSWORD:
        print("[FEHLER] Retraining fehlgeschlagen: Falsches Passwort.")
        return jsonify({'error': 'Falsches Passwort.'}), 401

    try:
        train_and_save_model()
        return jsonify({'message': 'Modell wird im Hintergrund neu trainiert.'})
    except Exception as e:
        print(f"[FEHLER] Fehler bei der API-Anfrage zum Neu-Trainieren: {str(e)}")
        return jsonify({'error': f'Ein Fehler beim Neu-Trainieren ist aufgetreten: {str(e)}'}), 500

@app.route('/get_data_status', methods=['GET'])
def get_data_status():
    password = request.args.get('password')
    if password != ADMIN_PASSWORD:
        return jsonify({'error': 'Falsches Passwort.'}), 401

    try:
        total_data = list(training_data_collection.find({}, {'_id': 0, 'text': 1, 'label': 1, 'trained': 1}))
        print("[LOG] Datenstatus erfolgreich abgerufen.")
        return jsonify({'data': total_data})
    except Exception as e:
        print(f"[FEHLER] Fehler beim Abrufen des Datenstatus: {str(e)}")
        return jsonify({'error': f'Fehler beim Abrufen der Daten: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)