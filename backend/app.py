# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)

# Einfaches Passwort für das Admin-Panel
ADMIN_PASSWORD = 'mozji' # ⚠️ ÄNDERE DIESES PASSWORT!

# Globale Variablen für das Modell, den Vektorizer und die Trainingsdaten
model = None
vectorizer = None
train_df = None

# Funktion zum Laden der Initialdaten und Trainieren des Modells
def train_and_save_model(texts_ki, texts_human):
    global model, vectorizer, train_df

    # DataFrame erstellen
    df_ki = pd.DataFrame({'text': texts_ki, 'label': 'ki'})
    df_human = pd.DataFrame({'text': texts_human, 'label': 'menschlich'})
    train_df = pd.concat([df_ki, df_human], ignore_index=True)

    # TF-IDF-Vektorizer erstellen
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(train_df['text'])
    y = train_df['label']

    # Naive Bayes-Modell trainieren
    model = MultinomialNB()
    model.fit(X, y)

    # Modell und Vektorizer speichern
    joblib.dump(model, 'model.pkl')
    joblib.dump(vectorizer, 'tokenizer.pkl')

    print("Modell und Vektorizer wurden erfolgreich neu trainiert und gespeichert.")

# Definieren der Initialdaten
# Diese Daten werden beim Start des Servers geladen.
initial_human_texts = [
    'Als ich gestern Abend durch den Wald spazierte, hörte ich plötzlich ein lautes Knacken hinter mir. Ich drehte mich um, sah aber nichts. Trotzdem beschleunigte ich meine Schritte, denn die Geräusche folgten mir. Es fühlte sich an, als ob die Bäume selbst mich beobachteten. Als ich endlich aus dem Wald trat, war ich völlig außer Atem und mein Herz pochte bis zum Hals. Ich werde so schnell nicht wieder im Dunkeln spazieren gehen.',
    'Meine Großmutter hat mir ein altes Familienrezept für Apfelkuchen gegeben. Es ist handgeschrieben auf einem zerknitterten Zettel, der Flecken von Zucker und Mehl hat. In dem Rezept steht, dass man die Äpfel nicht schälen soll, weil die Schale den Kuchen saftiger macht. Ich habe den Kuchen letztes Wochenende gebacken, und er war der beste, den ich je gegessen habe. Der Geruch erfüllte das ganze Haus mit warmen, würzigen Aromen. Es ist ein Rezept voller Erinnerungen und Liebe.',
    'Der letzte Roman von Haruki Murakami, den ich gelesen habe, war eine absolute Meisterleistung. Die Charaktere sind so tiefgründig und die Handlung ist surreal und doch so emotional. Ich saß stundenlang da und konnte das Buch einfach nicht aus der Hand legen. Jede Seite war wie ein Kunstwerk, voller Metaphern und versteckter Bedeutungen. Es hat mich noch lange nach dem Ende beschäftigt und zum Nachdenken angeregt.',
    'Nein ich denke nicht Pascal.',
    'Neeeeee',
    'Ich denke schon',
    'Die Quadratwurzel enthält einige Autos die ungenau sind.',
    'Ich vermute, dass die Wurzel drei ist',
    'Du bist dumm'
]

initial_ki_texts = [
    'Das grundlegende Prinzip der Quantenverschränkung beruht auf der nicht-lokalen Korrelation von Quantenzuständen. Zwei Partikel, die miteinander verschränkt sind, bleiben in einem Zustand, in dem die Messung eines Partikels den Zustand des anderen instantan beeinflusst, unabhängig von der räumlichen Entfernung. Dieses Phänomen, von Einstein als \'spukhafte Fernwirkung\' bezeichnet, ist eine fundamentale Eigenschaft der Quantenmechanik und bildet die Grundlage für Anwendungen in der Quantenkryptographie und dem Quantencomputing.',
    'Die Analyse der globalen Wirtschaftsindikatoren zeigt eine deutliche Verschiebung in Richtung digitaler Dienstleistungen. Das exponentielle Wachstum von E-Commerce-Plattformen, FinTech-Lösungen und Cloud-Computing-Infrastrukturen deutet auf eine zunehmende Abhängigkeit von technologischen Innovationen hin. Diese Entwicklung wird durch die steigende Nachfrage nach flexiblen und skalierbaren Geschäftsmodellen vorangetrieben, die eine Optimierung der Betriebsabläufe und eine erhöhte Effizienz ermöglichen. Die potenziellen Auswirkungen auf traditionelle Branchen sind signifikant und erfordern eine strategische Anpassung der Unternehmensstrukturen.',
    'Ein rekurrierendes neuronales Netzwerk (RNN) ist eine Klasse von künstlichen neuronalen Netzen, die sich durch die Fähigkeit auszeichnen, sequenzielle Daten wie Texte oder Zeitreihen zu verarbeiten. Im Gegensatz zu Feed-Forward-Netzwerken, bei denen Informationen nur in eine Richtung fließen, besitzen RNNs eine interne Schleife, die es ihnen ermöglicht, Informationen aus vorherigen Schritten zu speichern und in zukünftigen Schritten zu nutzen. Diese \'Gedächtnisfunktion\' macht sie ideal für Aufgaben wie Spracherkennung, natürliche Sprachverarbeitung und Zeitreihenanalyse, wo der Kontext vergangener Datenpunkte entscheidend ist.',
    'Auch wenn die Warnung nicht mehr erscheint, kann die Version auf dem Render-Server immer noch nicht exakt mit der Version deines Modells übereinstimmen, was zu diesem fehlerhaften Verhalten führt.',
    'Das wahrscheinlichste Problem ist, dass dein Modell oder der Vektorizer immer nur ein und dasselbe Ergebnis vorhersagen. Die Warnung über die inkonsistente Version wurde in diesem Log-Ausschnitt zwar nicht wiederholt, was gut ist, aber das bedeutet nicht unbedingt, dass das Problem behoben ist.',
    'Ja, die Logs zeigen, dass Anfragen an dein Backend gehen, aber etwas stimmt mit der Antwort nicht. Lass uns die Logs genauer analysieren, um herauszufinden, warum die Vorhersage nicht auf der Webseite angezeigt wird.',
    'Diese Frage kann ich nicht beantworten.'
]

# Beim Start des Servers initial trainieren
train_and_save_model(initial_ki_texts, initial_human_texts)


@app.route('/predict', methods=['POST'])
def predict():
    global model, vectorizer
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Kein Text bereitgestellt.'}), 400

    # Prüfen, ob Modell und Vektorizer geladen sind
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

# NEUER ENDPUNKT: Trainingsdaten abrufen
@app.route('/get_data', methods=['GET'])
def get_data():
    global train_df
    # Sende die aktuellen Trainingsdaten zurück
    return jsonify({
        'data': train_df.to_dict('records')
    })


# NEUER ENDPUNKT: Trainingsdaten speichern und Modell neu trainieren
@app.route('/save_data', methods=['POST'])
def save_data():
    global train_df
    data = request.json
    password = data.get('password')

    # Passwortprüfung
    if password != ADMIN_PASSWORD:
        return jsonify({'error': 'Falsches Passwort.'}), 401

    new_data = data.get('data')
    if not new_data:
        return jsonify({'error': 'Keine neuen Daten bereitgestellt.'}), 400

    # Konvertiere die neuen Daten in einen DataFrame und füge sie hinzu
    new_df = pd.DataFrame(new_data)
    train_df = pd.concat([train_df, new_df], ignore_index=True)

    # Modell mit den neuen Daten neu trainieren
    train_and_save_model(
        list(train_df[train_df['label'] == 'ki']['text']),
        list(train_df[train_df['label'] == 'menschlich']['text'])
    )

    return jsonify({'message': 'Modell erfolgreich neu trainiert mit neuen Daten!'})

if __name__ == '__main__':
    app.run(debug=True, port=5000) # Stelle sicher, dass der Port auf 5000 steht