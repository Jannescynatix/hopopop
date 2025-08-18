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
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize
from collections import Counter
import os
import bcrypt
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)

# --- NLTK-Daten herunterladen und überprüfen ---
def download_nltk_data():
    """Lädt die NLTK-Daten herunter, falls sie nicht vorhanden sind."""
    required_resources = ['punkt', 'punkt_tab']
    for resource in required_resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
            print(f"[LOG] NLTK-Daten '{resource}' bereits vorhanden.")
        except LookupError:
            print(f"[LOG] NLTK-Daten '{resource}' nicht gefunden. Starte Download...")
            try:
                nltk.download(resource, quiet=True)
                print(f"[LOG] NLTK-Daten '{resource}' erfolgreich heruntergeladen.")
            except Exception:
                print(f"[LOG] Globaler NLTK-Download für '{resource}' fehlgeschlagen. Versuche, in das Projektverzeichnis herunterzuladen.")
                nltk.download(resource, quiet=True, download_dir='.')
                print(f"[LOG] NLTK-Daten '{resource}' in das Projektverzeichnis heruntergeladen.")
                os.environ['NLTK_DATA'] = os.getcwd()

download_nltk_data()

# Sicheres Passwort-Handling
# Passwort-Hash aus Umgebungsvariable laden
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
if not ADMIN_PASSWORD_HASH:
    print("[WARNUNG] Umgebungsvariable ADMIN_PASSWORD_HASH ist nicht gesetzt. Admin-Login wird fehlschlagen.")
    # Für lokale Entwicklung kann ein Platzhalter verwendet werden, aber nicht für die Produktion!
    ADMIN_PASSWORD_HASH = '$2b$12$D23j9nZt2c9s5e7g8h3j2u9j2u9j2u9j2u9j2u9j2u9j2u9j2u9j'

# Token-Serializer für sichere Sessions
# Der geheime Schlüssel sollte ebenfalls eine Umgebungsvariable sein
SECRET_KEY = os.environ.get('SECRET_KEY', '518f95dd8db2a3c4a4f0b6c2ee4a7ca71db24afd7264a9b6bdf9484c067d7792')
s = URLSafeTimedSerializer(SECRET_KEY)

# Globale Variablen für das Modell und den Vektorizer
model = None

# MongoDB-Verbindung
MONGO_URI = 'mongodb+srv://wwll:k2AOWvBKW5H5oeZO@py.9gqajwk.mongodb.net/?retryWrites=true&w=majority&appName=py'
client = MongoClient(MONGO_URI)
db = client.ai_text_detector_db
training_data_collection = db.training_data

# --- Feature Engineering: Benutzerdefinierte Transformer ---
class TextFeaturesExtractor(BaseEstimator, TransformerMixin):
    """Extrahiert numerische Features aus Texten (z.B. Wortanzahl, Satzanzahl, Burstiness)."""
    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        if isinstance(X, pd.DataFrame):
            X = X['text']

        num_sentences = X.apply(lambda text: len(sent_tokenize(text)))
        num_words = X.apply(lambda text: len(text.split()))
        avg_word_length = X.apply(lambda text: sum(len(word) for word in text.split()) / len(text.split()) if len(text.split()) > 0 else 0)
        burstiness = X.apply(lambda text: np.std([len(sentence.split()) for sentence in sent_tokenize(text)]) if len(sent_tokenize(text)) > 1 else 0)

        return pd.DataFrame({
            'num_sentences': num_sentences,
            'num_words': num_words,
            'avg_word_length': avg_word_length,
            'burstiness': burstiness
        })

# --- Daten- und Modell-Logik ---
def seed_database():
    """Befüllt die Datenbank nur, wenn sie leer ist."""
    print("[LOG] Überprüfe Datenbank...")
    if training_data_collection.count_documents({}) == 0:
        print("[LOG] Datenbank ist leer. Befülle sie mit Initialdaten...")
        initial_human_texts = ['Als ich gestern Abend durch den Wald spazierte, hörte ich plötzlich ein lautes Knacken hinter mir. Ich drehte mich um, sah aber nichts. Trotzdem beschleunigte ich meine Schritte, denn die Geräusche folgten mir.',
                               'Meine Großmutter hat mir ein altes Familienrezept für Apfelkuchen gegeben. Es ist handgeschrieben auf einem zerknitterten Zettel, der Flecken von Zucker und Mehl hat.',
                               'Der letzte Roman von Haruki Murakami, den ich gelesen habe, war eine absolute Meisterleistung. Die Charaktere sind so tiefgründig und die Handlung ist surreal und doch so emotional.',
                               'Nein ich denke nicht Pascal.','Ich vermute, dass die Wurzel drei ist','Du bist dumm',
                               'Heute ist das Wetter wirklich schön, die Sonne scheint und es ist warm. Ich werde den Nachmittag im Park verbringen und ein Buch lesen.',
                               'Der Verkehr in der Stadt war heute eine Katastrophe. Ich habe fast eine Stunde gebraucht, um zur Arbeit zu kommen.',
                               'Mein Lieblingsessen ist Pizza mit extra Käse. Ich könnte sie jeden Tag essen, ohne dass sie mir über wird.',
                               'Das Konzert gestern war unglaublich! Die Band hat eine so tolle Energie auf die Bühne gebracht.',]
        initial_ki_texts = ['Das grundlegende Prinzip der Quantenverschränkung beruht auf der nicht-lokalen Korrelation von Quantenzuständen.',
                            'Die Analyse der globalen Wirtschaftsindikatoren zeigt eine deutliche Verschiebung in Richtung digitaler Dienstleistungen.',
                            'Ein rekurrierendes neuronales Netzwerk (RNN) ist eine Klasse von künstlichen neuronalen Netzen, die sich durch die Fähigkeit auszeichnen, sequenzielle Daten wie Texte oder Zeitreihen zu verarbeiten.',
                            'Das wahrscheinlichste Problem ist, dass dein Modell oder der Vektorizer immer nur ein und dasselbe Ergebnis vorhersagen.',
                            'Ja, die Logs zeigen, dass Anfragen an dein Backend gehen, aber etwas stimmt mit der Antwort nicht.',
                            'Diese Frage kann ich nicht beantworten.',
                            'Die Entwicklung nachhaltiger Energiesysteme erfordert die Integration erneuerbarer Quellen und eine effiziente Speicherung der erzeugten Energie.',
                            'In der modernen Linguistik wird der Begriff "Diskursanalyse" zur Untersuchung der sprachlichen Interaktion in ihrem sozialen Kontext verwendet.',
                            'Die Bedeutung des Internets der Dinge (IoT) wächst exponentiell, da immer mehr Geräte vernetzt werden und Daten austauschen.',
                            'Maschinelles Lernen bietet vielversprechende Ansätze zur Optimierung logistischer Prozesse und zur Vorhersage von Markttrends.']

        data_to_insert = [{'text': text, 'label': 'menschlich', 'trained': True} for text in initial_human_texts]
        data_to_insert.extend([{'text': text, 'label': 'ki', 'trained': True} for text in initial_ki_texts])
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

# Beim Start des Servers initial trainieren
seed_database()
train_and_save_model()

# --- Middleware zur Token-Validierung ---
def validate_token(token):
    try:
        data = s.loads(token, max_age=3600)  # Token ist 1 Stunde gültig
        if data.get('authenticated'):
            return True
    except (SignatureExpired, BadTimeSignature):
        return False
    return False

# Funktion zur Berechnung der Statistiken
def calculate_stats(data):
    stats = {
        'word_counts': {'menschlich': 0, 'ki': 0, 'total': 0},
        'char_counts': {'menschlich': 0, 'ki': 0, 'total': 0},
        'avg_lengths': {'menschlich': 0, 'ki': 0},
        'frequent_words': {'menschlich': [], 'ki': [], 'total': []}
    }

    human_texts = [d['text'] for d in data if d['label'] == 'menschlich']
    ki_texts = [d['text'] for d in data if d['label'] == 'ki']
    all_texts = human_texts + ki_texts

    # Berechnung der Zählungen
    for text in human_texts:
        words = text.split()
        stats['word_counts']['menschlich'] += len(words)
        # NEU: Leerzeichen entfernen, bevor die Zeichen gezählt werden
        stats['char_counts']['menschlich'] += len(text.replace(" ", ""))

    for text in ki_texts:
        words = text.split()
        stats['word_counts']['ki'] += len(words)
        # NEU: Leerzeichen entfernen, bevor die Zeichen gezählt werden
        stats['char_counts']['ki'] += len(text.replace(" ", ""))

    stats['word_counts']['total'] = stats['word_counts']['menschlich'] + stats['word_counts']['ki']
    stats['char_counts']['total'] = stats['char_counts']['menschlich'] + stats['char_counts']['ki']

    # Berechnung der durchschnittlichen Länge
    if len(human_texts) > 0:
        stats['avg_lengths']['menschlich'] = stats['char_counts']['menschlich'] / len(human_texts)
    if len(ki_texts) > 0:
        stats['avg_lengths']['ki'] = stats['char_counts']['ki'] / len(ki_texts)

    # Berechnung der häufigsten Wörter
    def get_frequent_words(text_list, num=15):
        all_words = ' '.join(text_list).lower()
        # Entferne Satzzeichen
        all_words = re.sub(r'[^\w\s]', '', all_words)
        words = all_words.split()
        return Counter(words).most_common(num)

    stats['frequent_words']['menschlich'] = get_frequent_words(human_texts)
    stats['frequent_words']['ki'] = get_frequent_words(ki_texts)
    stats['frequent_words']['total'] = get_frequent_words(all_texts)

    return stats

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
    password = data.get('password').encode('utf-8')

    if ADMIN_PASSWORD_HASH and bcrypt.checkpw(password, ADMIN_PASSWORD_HASH.encode('utf-8')):
        print("[LOG] Admin-Login erfolgreich.")
        training_data_list = list(training_data_collection.find({}, {'_id': 0}))
        token = s.dumps({'authenticated': True})
        stats = calculate_stats(training_data_list)
        return jsonify({'message': 'Login erfolgreich', 'data': training_data_list, 'token': token, 'stats': stats})
    else:
        print("[FEHLER] Admin-Login fehlgeschlagen: Falsches Passwort.")
        return jsonify({'error': 'Falsches Passwort.'}), 401

@app.route('/add_data', methods=['POST'])
def add_data():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not validate_token(auth_header.split(' ')[1]):
        print("[FEHLER] Daten hinzufügen fehlgeschlagen: Ungültiger Token.")
        return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

    data = request.json
    text = data.get('text')
    label = data.get('label')

    if not text or not label:
        print("[FEHLER] Daten hinzufügen fehlgeschlagen: Text und Label fehlen.")
        return jsonify({'error': 'Text und Label sind erforderlich.'}), 400

    training_data_collection.insert_one({'text': text, 'label': label, 'trained': False})
    print(f"[LOG] Neuer Datensatz ({label}) zur Warteschlange hinzugefügt: '{text[:30]}...'")
    return jsonify({'message': 'Daten erfolgreich zur Trainingswarteschlange hinzugefügt!'})

@app.route('/delete_data', methods=['POST'])
def delete_data():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not validate_token(auth_header.split(' ')[1]):
        print("[FEHLER] Daten löschen fehlgeschlagen: Ungültiger Token.")
        return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

    data = request.json
    text_to_delete = data.get('text')

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

@app.route('/retrain_model', methods=['POST'])
def retrain_model():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not validate_token(auth_header.split(' ')[1]):
        print("[FEHLER] Retraining fehlgeschlagen: Ungültiger Token.")
        return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

    try:
        train_and_save_model()
        return jsonify({'message': 'Modell wird im Hintergrund neu trainiert.'})
    except Exception as e:
        print(f"[FEHLER] Fehler bei der API-Anfrage zum Neu-Trainieren: {str(e)}")
        return jsonify({'error': f'Ein Fehler beim Neu-Trainieren ist aufgetreten: {str(e)}'}), 500

@app.route('/get_data_status', methods=['GET'])
def get_data_status():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not validate_token(auth_header.split(' ')[1]):
        return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

    try:
        total_data = list(training_data_collection.find({}, {'_id': 0, 'text': 1, 'label': 1, 'trained': 1}))
        stats = calculate_stats(total_data)
        print("[LOG] Datenstatus erfolgreich abgerufen.")
        return jsonify({'data': total_data, 'stats': stats})
    except Exception as e:
        print(f"[FEHLER] Fehler beim Abrufen des Datenstatus: {str(e)}")
        return jsonify({'error': f'Fehler beim Abrufen der Daten: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)



    neuste: # backend/app.py
            from flask import Flask, request, jsonify
            from flask_cors import CORS
            import joblib
            import pandas as pd
            from pymongo import MongoClient
            import re
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.pipeline import Pipeline
            # WICHTIGE ÄNDERUNG: Importiere RandomForestClassifier statt MultinomialNB
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.base import BaseEstimator, TransformerMixin
            from sklearn.compose import ColumnTransformer
            import numpy as np
            import nltk
            from nltk.tokenize import sent_tokenize
            from collections import Counter
            import os
            import bcrypt
            from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
            # NEU: Importiere die Stoppwortliste
            from nltk.corpus import stopwords

            # Flask-App initialisieren
            app = Flask(__name__)
            CORS(app)

            # --- NLTK-Daten herunterladen und überprüfen ---
            # --- NLTK-Daten herunterladen und überprüfen ---
            def download_nltk_data():
                """Lädt die NLTK-Daten herunter, falls sie nicht vorhanden sind."""
                required_resources = ['punkt', 'stopwords', 'punkt_tab'] # NEU: Füge 'punkt_tab' hinzu
                for resource in required_resources:
                    try:
                        # Überprüfe, ob die Ressource existiert
                        if resource in ['punkt', 'punkt_tab']:
                            nltk.data.find(f'tokenizers/{resource}')
                        else:
                            nltk.data.find(f'corpora/{resource}')

                        print(f"[LOG] NLTK-Daten '{resource}' bereits vorhanden.")
                    except LookupError:
                        print(f"[LOG] NLTK-Daten '{resource}' nicht gefunden. Starte Download...")
                        try:
                            # Versuche, die Ressource herunterzuladen
                            nltk.download(resource, quiet=True)
                            print(f"[LOG] NLTK-Daten '{resource}' erfolgreich heruntergeladen.")
                        except Exception:
                            print(f"[LOG] Globaler NLTK-Download für '{resource}' fehlgeschlagen. Versuche, in das Projektverzeichnis herunterzuladen.")
                            # Lade in das Projektverzeichnis herunter, falls es einen Fehler gibt
                            nltk.download(resource, quiet=True, download_dir='.')
                            print(f"[LOG] NLTK-Daten '{resource}' in das Projektverzeichnis heruntergeladen.")
                            os.environ['NLTK_DATA'] = os.getcwd()

            download_nltk_data()

            # Lade die deutsche Stoppwortliste
            german_stopwords = stopwords.words('german')

            # Sicheres Passwort-Handling
            # Passwort-Hash aus Umgebungsvariable laden
            ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
            if not ADMIN_PASSWORD_HASH:
                print("[WARNUNG] Umgebungsvariable ADMIN_PASSWORD_HASH ist nicht gesetzt. Admin-Login wird fehlschlagen.")
                # Für lokale Entwicklung kann ein Platzhalter verwendet werden, aber nicht für die Produktion!
                ADMIN_PASSWORD_HASH = '$2b$12$D23j9nZt2c9s5e7g8h3j2u9j2u9j2u9j2u9j2u9j2u9j2u9j2u9j'

            # Token-Serializer für sichere Sessions
            # Der geheime Schlüssel sollte ebenfalls eine Umgebungsvariable sein
            SECRET_KEY = os.environ.get('SECRET_KEY', '518f95dd8db2a3c4a4f0b6c2ee4a7ca71db24afd7264a9b6bdf9484c067d7792')
            s = URLSafeTimedSerializer(SECRET_KEY)

            # Globale Variablen für das Modell und den Vektorizer
            model = None

            # MongoDB-Verbindung
            MONGO_URI = 'mongodb+srv://wwll:k2AOWvBKW5H5oeZO@py.9gqajwk.mongodb.net/?retryWrites=true&w=majority&appName=py'
            client = MongoClient(MONGO_URI)
            db = client.ai_text_detector_db
            training_data_collection = db.training_data

            # --- Feature Engineering: Benutzerdefinierte Transformer ---
            class TextFeaturesExtractor(BaseEstimator, TransformerMixin):
                """Extrahiert numerische Features aus Texten (z.B. Wortanzahl, Satzanzahl, Burstiness)."""
                def fit(self, X, y=None):
                    return self

                def transform(self, X, y=None):
                    if isinstance(X, pd.DataFrame):
                        X = X['text']

                    num_sentences = X.apply(lambda text: len(sent_tokenize(text)))
                    num_words = X.apply(lambda text: len(text.split()))
                    avg_word_length = X.apply(lambda text: sum(len(word) for word in text.split()) / len(text.split()) if len(text.split()) > 0 else 0)
                    burstiness = X.apply(lambda text: np.std([len(sentence.split()) for sentence in sent_tokenize(text)]) if len(sent_tokenize(text)) > 1 else 0)
                    # NEUE FEATURES: Zähle Satzzeichen und Ziffern
                    num_punctuation = X.apply(lambda text: len(re.findall(r'[.,;?!-]', text)))
                    num_digits = X.apply(lambda text: len(re.findall(r'\d', text)))

                    return pd.DataFrame({
                        'num_sentences': num_sentences,
                        'num_words': num_words,
                        'avg_word_length': avg_word_length,
                        'burstiness': burstiness,
                        'num_punctuation': num_punctuation,
                        'num_digits': num_digits
                    })

            # --- Daten- und Modell-Logik ---
            def seed_database():
                """Befüllt die Datenbank nur, wenn sie leer ist."""
                print("[LOG] Überprüfe Datenbank...")
                if training_data_collection.count_documents({}) == 0:
                    print("[LOG] Datenbank ist leer. Befülle sie mit Initialdaten...")
                    initial_human_texts = ['Als ich gestern Abend durch den Wald spazierte, hörte ich plötzlich ein lautes Knacken hinter mir. Ich drehte mich um, sah aber nichts. Trotzdem beschleunigte ich meine Schritte, denn die Geräusche folgten mir.',
                                           'Meine Großmutter hat mir ein altes Familienrezept für Apfelkuchen gegeben. Es ist handgeschrieben auf einem zerknitterten Zettel, der Flecken von Zucker und Mehl hat.',
                                           'Der letzte Roman von Haruki Murakami, den ich gelesen habe, war eine absolute Meisterleistung. Die Charaktere sind so tiefgründig und die Handlung ist surreal und doch so emotional.',
                                           'Nein ich denke nicht Pascal.','Ich vermute, dass die Wurzel drei ist','Du bist dumm',
                                           'Heute ist das Wetter wirklich schön, die Sonne scheint und es ist warm. Ich werde den Nachmittag im Park verbringen und ein Buch lesen.',
                                           'Der Verkehr in der Stadt war heute eine Katastrophe. Ich habe fast eine Stunde gebraucht, um zur Arbeit zu kommen.',
                                           'Mein Lieblingsessen ist Pizza mit extra Käse. Ich könnte sie jeden Tag essen, ohne dass sie mir über wird.',
                                           'Das Konzert gestern war unglaublich! Die Band hat eine so tolle Energie auf die Bühne gebracht.',]
                    initial_ki_texts = ['Das grundlegende Prinzip der Quantenverschränkung beruht auf der nicht-lokalen Korrelation von Quantenzuständen.',
                                        'Die Analyse der globalen Wirtschaftsindikatoren zeigt eine deutliche Verschiebung in Richtung digitaler Dienstleistungen.',
                                        'Ein rekurrierendes neuronales Netzwerk (RNN) ist eine Klasse von künstlichen neuronalen Netzen, die sich durch die Fähigkeit auszeichnen, sequenzielle Daten wie Texte oder Zeitreihen zu verarbeiten.',
                                        'Das wahrscheinlichste Problem ist, dass dein Modell oder der Vektorizer immer nur ein und dasselbe Ergebnis vorhersagen.',
                                        'Ja, die Logs zeigen, dass Anfragen an dein Backend gehen, aber etwas stimmt mit der Antwort nicht.',
                                        'Diese Frage kann ich nicht beantworten.',
                                        'Die Entwicklung nachhaltiger Energiesysteme erfordert die Integration erneuerbarer Quellen und eine effiziente Speicherung der erzeugten Energie.',
                                        'In der modernen Linguistik wird der Begriff "Diskursanalyse" zur Untersuchung der sprachlichen Interaktion in ihrem sozialen Kontext verwendet.',
                                        'Die Bedeutung des Internets der Dinge (IoT) wächst exponentiell, da immer mehr Geräte vernetzt werden und Daten austauschen.',
                                        'Maschinelles Lernen bietet vielversprechende Ansätze zur Optimierung logistischer Prozesse und zur Vorhersage von Markttrends.']

                    data_to_insert = [{'text': text, 'label': 'menschlich', 'trained': True} for text in initial_human_texts]
                    data_to_insert.extend([{'text': text, 'label': 'ki', 'trained': True} for text in initial_ki_texts])
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

                    # NEUE: Stoppwörter zum TfidfVectorizer hinzufügen
                    preprocessor = ColumnTransformer(
                        transformers=[
                            ('text_tfidf', TfidfVectorizer(ngram_range=(1, 3), max_features=1000, stop_words=german_stopwords), 'text'),
                            ('text_features', TextFeaturesExtractor(), 'text')
                        ],
                        remainder='passthrough'
                    )

                    model = Pipeline(steps=[
                        ('preprocessor', preprocessor),
                        # WICHTIGE ÄNDERUNG: Nutze RandomForestClassifier
                        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
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

            # Beim Start des Servers initial trainieren
            seed_database()
            train_and_save_model()

            # --- Middleware zur Token-Validierung ---
            def validate_token(token):
                try:
                    data = s.loads(token, max_age=3600)  # Token ist 1 Stunde gültig
                    if data.get('authenticated'):
                        return True
                except (SignatureExpired, BadTimeSignature):
                    return False
                return False

            # Funktion zur Berechnung der Statistiken
            def calculate_stats(data):
                stats = {
                    'word_counts': {'menschlich': 0, 'ki': 0, 'total': 0},
                    'char_counts': {'menschlich': 0, 'ki': 0, 'total': 0},
                    'avg_lengths': {'menschlich': 0, 'ki': 0},
                    'frequent_words': {'menschlich': [], 'ki': [], 'total': []}
                }

                human_texts = [d['text'] for d in data if d['label'] == 'menschlich']
                ki_texts = [d['text'] for d in data if d['label'] == 'ki']
                all_texts = human_texts + ki_texts

                # Berechnung der Zählungen
                for text in human_texts:
                    words = text.split()
                    stats['word_counts']['menschlich'] += len(words)
                    # Leerzeichen entfernen, bevor die Zeichen gezählt werden
                    stats['char_counts']['menschlich'] += len(text.replace(" ", ""))

                for text in ki_texts:
                    words = text.split()
                    stats['word_counts']['ki'] += len(words)
                    # Leerzeichen entfernen, bevor die Zeichen gezählt werden
                    stats['char_counts']['ki'] += len(text.replace(" ", ""))

                stats['word_counts']['total'] = stats['word_counts']['menschlich'] + stats['word_counts']['ki']
                stats['char_counts']['total'] = stats['char_counts']['menschlich'] + stats['char_counts']['ki']

                # Berechnung der durchschnittlichen Länge
                if len(human_texts) > 0:
                    stats['avg_lengths']['menschlich'] = stats['char_counts']['menschlich'] / len(human_texts)
                if len(ki_texts) > 0:
                    stats['avg_lengths']['ki'] = stats['char_counts']['ki'] / len(ki_texts)

                # Berechnung der häufigsten Wörter
                def get_frequent_words(text_list, num=15):
                    all_words = ' '.join(text_list).lower()
                    # Entferne Satzzeichen
                    all_words = re.sub(r'[^\w\s]', '', all_words)
                    words = all_words.split()
                    return Counter(words).most_common(num)

                stats['frequent_words']['menschlich'] = get_frequent_words(human_texts)
                stats['frequent_words']['ki'] = get_frequent_words(ki_texts)
                stats['frequent_words']['total'] = get_frequent_words(all_texts)

                return stats

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

                    # Die Reihenfolge der Klassen kann variieren, daher suchen wir nach den richtigen Indizes
                    mensch_prob = probabilities[list(classes).index('menschlich')] * 100
                    ki_prob = probabilities[list(classes).index('ki')] * 100

                    print(f"[LOG] Vorhersage für Text: '{text[:30]}...'. Ergebnis: Menschlich: {round(mensch_prob, 2)}%, KI: {round(ki_prob, 2)}%")

                    return jsonify({
                        'menschlich': round(mensch_prob, 2),
                        'ki': round(ki_prob, 2)
                    })

                except Exception as e:
                    print(f"[FEHLER] Vorhersage konnte nicht durchgeführt werden: {str(e)}")
                    return jsonify({'error': 'Ein Fehler bei der Vorhersage ist aufgetreten.'}), 500

            @app.route('/admin_login', methods=['POST'])
            def admin_login():
                data = request.json
                password = data.get('password').encode('utf-8')

                if ADMIN_PASSWORD_HASH and bcrypt.checkpw(password, ADMIN_PASSWORD_HASH.encode('utf-8')):
                    print("[LOG] Admin-Login erfolgreich.")
                    training_data_list = list(training_data_collection.find({}, {'_id': 0}))
                    token = s.dumps({'authenticated': True})
                    stats = calculate_stats(training_data_list)
                    return jsonify({'message': 'Login erfolgreich', 'data': training_data_list, 'token': token, 'stats': stats})
                else:
                    print("[FEHLER] Admin-Login fehlgeschlagen: Falsches Passwort.")
                    return jsonify({'error': 'Falsches Passwort.'}), 401

            @app.route('/add_data', methods=['POST'])
            def add_data():
                auth_header = request.headers.get('Authorization')
                if not auth_header or not validate_token(auth_header.split(' ')[1]):
                    print("[FEHLER] Daten hinzufügen fehlgeschlagen: Ungültiger Token.")
                    return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

                data = request.json
                text = data.get('text')
                label = data.get('label')

                if not text or not label:
                    print("[FEHLER] Daten hinzufügen fehlgeschlagen: Text und Label fehlen.")
                    return jsonify({'error': 'Text und Label sind erforderlich.'}), 400

                training_data_collection.insert_one({'text': text, 'label': label, 'trained': False})
                print(f"[LOG] Neuer Datensatz ({label}) zur Warteschlange hinzugefügt: '{text[:30]}...'")
                return jsonify({'message': 'Daten erfolgreich zur Trainingswarteschlange hinzugefügt!'})

            @app.route('/delete_data', methods=['POST'])
            def delete_data():
                auth_header = request.headers.get('Authorization')
                if not auth_header or not validate_token(auth_header.split(' ')[1]):
                    print("[FEHLER] Daten löschen fehlgeschlagen: Ungültiger Token.")
                    return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

                data = request.json
                text_to_delete = data.get('text')

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

            @app.route('/retrain_model', methods=['POST'])
            def retrain_model():
                auth_header = request.headers.get('Authorization')
                if not auth_header or not validate_token(auth_header.split(' ')[1]):
                    print("[FEHLER] Retraining fehlgeschlagen: Ungültiger Token.")
                    return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

                try:
                    train_and_save_model()
                    return jsonify({'message': 'Modell wird im Hintergrund neu trainiert.'})
                except Exception as e:
                    print(f"[FEHLER] Fehler bei der API-Anfrage zum Neu-Trainieren: {str(e)}")
                    return jsonify({'error': f'Ein Fehler beim Neu-Trainieren ist aufgetreten: {str(e)}'}), 500

            @app.route('/get_data_status', methods=['GET'])
            def get_data_status():
                auth_header = request.headers.get('Authorization')
                if not auth_header or not validate_token(auth_header.split(' ')[1]):
                    return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

                try:
                    total_data = list(training_data_collection.find({}, {'_id': 0, 'text': 1, 'label': 1, 'trained': 1}))
                    stats = calculate_stats(total_data)
                    print("[LOG] Datenstatus erfolgreich abgerufen.")
                    return jsonify({'data': total_data, 'stats': stats})
                except Exception as e:
                    print(f"[FEHLER] Fehler beim Abrufen des Datenstatus: {str(e)}")
                    return jsonify({'error': f'Fehler beim Abrufen der Daten: {str(e)}'}), 500

            if __name__ == '__main__':
                app.run(debug=True)