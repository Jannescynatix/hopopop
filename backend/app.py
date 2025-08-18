# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from pymongo import MongoClient
import re
from collections import Counter
import os
import bcrypt
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

# NEUE IMPORTE
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, AdamW
import numpy as np

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)

# Sicheres Passwort-Handling
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '$2b$12$D23j9nZt2c9s5e7g8h3j2u9j2u9j2u9j2u9j2u9j2u9j2u9j2u9j')
SECRET_KEY = os.environ.get('SECRET_KEY', '518f95dd8db2a3c4a4f0b6c2ee4a7ca71db24afd7264a9b6bdf9484c067d7792')
s = URLSafeTimedSerializer(SECRET_KEY)

# Globale Variablen
model = None
tokenizer = None

# MongoDB-Verbindung
MONGO_URI = 'mongodb+srv://wwll:k2AOWvBKW5H5oeZO@py.9gqajwk.mongodb.net/?retryWrites=true&w=majority&appName=py'
client = MongoClient(MONGO_URI)
db = client.ai_text_detector_db
training_data_collection = db.training_data

# Klassendefinition für das Deep-Learning-Modell
class TextClassificationDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        label = self.labels[item]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'text': text,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# Funktion zur Berechnung der Statistiken (bleibt gleich)
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
    for text in human_texts:
        words = text.split()
        stats['word_counts']['menschlich'] += len(words)
        stats['char_counts']['menschlich'] += len(text.replace(" ", ""))
    for text in ki_texts:
        words = text.split()
        stats['word_counts']['ki'] += len(words)
        stats['char_counts']['ki'] += len(text.replace(" ", ""))
    stats['word_counts']['total'] = stats['word_counts']['menschlich'] + stats['word_counts']['ki']
    stats['char_counts']['total'] = stats['char_counts']['menschlich'] + stats['char_counts']['ki']
    if len(human_texts) > 0:
        stats['avg_lengths']['menschlich'] = stats['char_counts']['menschlich'] / len(human_texts)
    if len(ki_texts) > 0:
        stats['avg_lengths']['ki'] = stats['char_counts']['ki'] / len(ki_texts)
    def get_frequent_words(text_list, num=15):
        all_words = ' '.join(text_list).lower()
        all_words = re.sub(r'[^\w\s]', '', all_words)
        words = all_words.split()
        return Counter(words).most_common(num)
    stats['frequent_words']['menschlich'] = get_frequent_words(human_texts)
    stats['frequent_words']['ki'] = get_frequent_words(ki_texts)
    stats['frequent_words']['total'] = get_frequent_words(all_texts)
    return stats

# Funktion zum Training und Speichern des Deep-Learning-Modells
def train_and_save_model():
    global model, tokenizer
    print("[LOG] Starte Deep-Learning Modell-Training...")
    try:
        training_data_list = list(training_data_collection.find({'trained': True}, {'_id': 0}))
        if not training_data_list:
            print("[LOG] Keine trainierbaren Daten in der Datenbank gefunden.")
            model = None
            tokenizer = None
            return

        df = pd.DataFrame(training_data_list)
        df['label_id'] = df['label'].map({'menschlich': 0, 'ki': 1})
        print(f"[LOG] {len(df)} Datensätze für das Training geladen.")

        tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-german-cased')
        model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-german-cased', num_labels=2)

        MAX_LEN = 256
        EPOCHS = 3
        BATCH_SIZE = 8

        dataset = TextClassificationDataset(
            texts=df.text.to_numpy(),
            labels=df.label_id.to_numpy(),
            tokenizer=tokenizer,
            max_len=MAX_LEN
        )

        data_loader = DataLoader(dataset, batch_size=BATCH_SIZE)

        optimizer = AdamW(model.parameters(), lr=2e-5, correct_bias=False)

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = model.to(device)

        model.train()
        for epoch in range(EPOCHS):
            print(f"--- Epoch {epoch + 1}/{EPOCHS} ---")
            for d in data_loader:
                input_ids = d['input_ids'].to(device)
                attention_mask = d['attention_mask'].to(device)
                labels = d['labels'].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

        torch.save(model.state_dict(), 'bert_model_state.bin')
        joblib.dump(tokenizer, 'bert_tokenizer.pkl')

        print("[LOG] Deep-Learning-Modell wurde erfolgreich neu trainiert und gespeichert.")
        training_data_collection.update_many({'trained': False}, {'$set': {'trained': True}})
        print("[LOG] Alle neuen Daten als 'trained' markiert.")
        print("[STATUS] TRAINING ABGESCHLOSSEN.")

    except Exception as e:
        print(f"[FEHLER] Fehler beim Neu-Trainieren des Modells: {str(e)}")
        import traceback
        traceback.print_exc()

# Beim Start des Servers initial trainieren
seed_database()
train_and_save_model()

# --- Middleware zur Token-Validierung ---
def validate_token(token):
    try:
        data = s.loads(token, max_age=3600)
        if data.get('authenticated'):
            return True
    except (SignatureExpired, BadTimeSignature):
        return False
    return False

# --- API Endpunkte ---
@app.route('/predict', methods=['POST'])
def predict():
    global model, tokenizer
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Kein Text bereitgestellt.'}), 400

    if model is None or tokenizer is None:
        return jsonify({'error': 'Das Modell ist noch nicht geladen oder trainiert.'}), 500

    try:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model.eval()

        encoding = tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=256,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        input_ids = encoding['input_ids'].to(device)
        attention_mask = encoding['attention_mask'].to(device)

        with torch.no_grad():
            outputs = model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1).flatten().tolist()

        mensch_prob = probabilities[0] * 100
        ki_prob = probabilities[1] * 100

        print(f"[LOG] Vorhersage für Text: '{text[:30]}...'. Ergebnis: Menschlich: {round(mensch_prob, 2)}%, KI: {round(ki_prob, 2)}%")

        return jsonify({
            'menschlich': round(mensch_prob, 2),
            'ki': round(ki_prob, 2)
        })

    except Exception as e:
        print(f"[FEHLER] Vorhersage konnte nicht durchgeführt werden: {str(e)}")
        import traceback
        traceback.print_exc()
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