# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import os
import bcrypt
import pandas as pd
from worker import train_and_save_model, get_prediction, add_data_to_db, delete_data_from_db, get_data_status_from_db, ADMIN_PASSWORD_HASH

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)

# Token-Serializer für sichere Sessions
SECRET_KEY = os.environ.get('SECRET_KEY', None)
if not SECRET_KEY:
    print("[WARNUNG] Umgebungsvariable SECRET_KEY ist nicht gesetzt. Session-Token sind unsicher.")
    SECRET_KEY = 'fallback_secret_key' # NICHT FÜR DIE PRODUKTION VERWENDEN
s = URLSafeTimedSerializer(SECRET_KEY)

# --- Middleware zur Token-Validierung ---
def validate_token(token):
    try:
        data = s.loads(token, max_age=3600)  # Token ist 1 Stunde gültig
        if data.get('authenticated'):
            return True
    except (SignatureExpired, BadTimeSignature):
        return False
    return False

# --- API Endpunkte ---
@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Kein Text bereitgestellt.'}), 400

    try:
        text_df = pd.DataFrame([{'text': text}])
        probabilities = get_prediction(text_df)
        print(f"[LOG] Vorhersage für Text: '{text[:30]}...'. Ergebnis: Menschlich: {probabilities['menschlich']}%, KI: {probabilities['ki']}%")
        return jsonify(probabilities)

    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"[FEHLER] Vorhersage konnte nicht durchgeführt werden: {str(e)}")
        return jsonify({'error': 'Ein Fehler bei der Vorhersage ist aufgetreten.'}), 500

@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get('password').encode('utf-8')

    if ADMIN_PASSWORD_HASH and bcrypt.checkpw(password, ADMIN_PASSWORD_HASH.encode('utf-8')):
        print("[LOG] Admin-Login erfolgreich.")
        token = s.dumps({'authenticated': True})
        return jsonify({'message': 'Login erfolgreich', 'token': token})
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

    try:
        add_data_to_db(text, label)
        return jsonify({'message': 'Daten erfolgreich zur Trainingswarteschlange hinzugefügt!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

    try:
        deleted_count = delete_data_from_db(text_to_delete)
        if deleted_count > 0:
            print(f"[LOG] Datensatz erfolgreich gelöscht: '{text_to_delete[:30]}...'")
            return jsonify({'message': 'Daten erfolgreich gelöscht.'})
        else:
            print("[FEHLER] Daten löschen fehlgeschlagen: Text nicht in der DB gefunden.")
            return jsonify({'error': 'Text nicht gefunden.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/retrain_model', methods=['POST'])
def retrain_model():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not validate_token(auth_header.split(' ')[1]):
        print("[FEHLER] Retraining fehlgeschlagen: Ungültiger Token.")
        return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

    try:
        train_and_save_model()
        return jsonify({'message': 'Modell wurde erfolgreich neu trainiert.'})
    except Exception as e:
        print(f"[FEHLER] Fehler bei der API-Anfrage zum Neu-Trainieren: {str(e)}")
        return jsonify({'error': f'Ein Fehler beim Neu-Trainieren ist aufgetreten: {str(e)}'}), 500

@app.route('/get_data_status', methods=['GET'])
def get_data_status():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not validate_token(auth_header.split(' ')[1]):
        return jsonify({'error': 'Autorisierung fehlgeschlagen.'}), 401

    try:
        total_data, word_counts = get_data_status_from_db()
        print("[LOG] Datenstatus erfolgreich abgerufen.")
        return jsonify({'data': total_data, 'word_counts': word_counts})
    except Exception as e:
        print(f"[FEHLER] Fehler beim Abrufen des Datenstatus: {str(e)}")
        return jsonify({'error': f'Fehler beim Abrufen der Daten: {str(e)}'}), 500

if __name__ == '__main__':
    # Initiales Setup und Training
    from worker import download_nltk_data, seed_database, train_and_save_model
    download_nltk_data()
    seed_database()
    train_and_save_model()
    app.run(debug=True)