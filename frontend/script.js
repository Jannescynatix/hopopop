// frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Haupt-App-Elemente
    const mainApp = document.getElementById('main-app');
    const analyzeBtn = document.getElementById('analyze-btn');
    const textInput = document.getElementById('text-input');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    const kiBar = document.querySelector('.ki-bar');
    const menschBar = document.querySelector('.mensch-bar');
    const kiLabel = document.getElementById('ki-label');
    const menschLabel = document.getElementById('mensch-label');
    const adminLoginBtn = document.getElementById('admin-login-btn');

    // Admin-Panel-Elemente
    const adminPanel = document.getElementById('admin-panel');
    const loginForm = document.getElementById('login-form');
    const passwordInput = document.getElementById('admin-password-input');
    const passwordSubmitBtn = document.getElementById('password-submit-btn');
    const loginErrorMsg = document.getElementById('login-error-msg');
    const trainingDataView = document.getElementById('training-data-view');
    const newTextInput = document.getElementById('new-text-input');
    const addHumanBtn = document.getElementById('add-human-btn');
    const addKiBtn = document.getElementById('add-ki-btn');
    const dataList = document.getElementById('data-list');
    const saveDataBtn = document.getElementById('save-data-btn');
    const saveStatusMsg = document.getElementById('save-status-msg');
    const backToMainBtn = document.getElementById('back-to-main-btn');

    // **WICHTIG:** Ersetze DIESE URL durch die URL deiner gehosteten Render-App
    const API_BASE_URL = 'https://b-kb9u.onrender.com';
    const PREDICT_URL = `${API_BASE_URL}/predict`;
    const GET_DATA_URL = `${API_BASE_URL}/get_data`;
    const SAVE_DATA_URL = `${API_BASE_URL}/save_data`;

    let currentTrainingData = [];

    // --- Haupt-App-Logik ---
    analyzeBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();

        if (text.length === 0) {
            alert('Bitte geben Sie einen Text ein, um die Analyse zu starten.');
            return;
        }

        resultContainer.classList.add('hidden');
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analysiere...';

        try {
            const response = await fetch(PREDICT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });

            const data = await response.json();

            if (response.ok) {
                const kiProb = data.ki;
                const menschProb = data.menschlich;

                // Ergebnis anzeigen
                resultContainer.classList.remove('hidden');

                if (kiProb > menschProb) {
                    resultText.textContent = `Dieser Text wurde wahrscheinlich von einer KI generiert.`;
                } else {
                    resultText.textContent = `Dieser Text wurde wahrscheinlich von einem Menschen geschrieben.`;
                }

                // Fortschrittsbalken aktualisieren
                kiBar.style.width = `${kiProb}%`;
                menschBar.style.width = `${menschProb}%`;
                kiLabel.textContent = `KI: ${kiProb}%`;
                menschLabel.textContent = `Menschlich: ${menschProb}%`;
            } else {
                resultText.textContent = `Fehler: ${data.error}`;
            }

        } catch (error) {
            console.error('Fehler bei der API-Anfrage:', error);
            resultText.textContent = 'Es gab ein Problem bei der Verbindung zur API.';
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analysieren';
        }
    });

    // --- Admin-Logik ---

    adminLoginBtn.addEventListener('click', () => {
        mainApp.classList.add('hidden');
        adminPanel.classList.remove('hidden');
    });

    backToMainBtn.addEventListener('click', () => {
        adminPanel.classList.add('hidden');
        mainApp.classList.remove('hidden');
    });

    passwordSubmitBtn.addEventListener('click', async () => {
        const password = passwordInput.value;
        // Einfache Prüfung, um unnötige Anfragen zu vermeiden
        if (!password) {
            loginErrorMsg.textContent = 'Bitte Passwort eingeben.';
            return;
        }

        // Simuliere die Passwortprüfung auf dem Backend
        // Hier fragen wir die Daten ab, wenn das Passwort korrekt ist
        try {
            const response = await fetch(GET_DATA_URL);
            if (response.ok) {
                const data = await response.json();
                currentTrainingData = data.data;
                renderTrainingData();
                loginForm.classList.add('hidden');
                trainingDataView.classList.remove('hidden');
            } else {
                loginErrorMsg.textContent = 'Falsches Passwort oder Fehler beim Laden der Daten.';
            }
        } catch (error) {
            loginErrorMsg.textContent = 'Verbindungsfehler zur API.';
            console.error(error);
        }
    });

    // Funktion zum Hinzufügen von Texten zur Liste
    function addTextToList(label) {
        const text = newTextInput.value.trim();
        if (text) {
            currentTrainingData.push({ text, label });
            newTextInput.value = '';
            renderTrainingData();
        }
    }

    addHumanBtn.addEventListener('click', () => addTextToList('menschlich'));
    addKiBtn.addEventListener('click', () => addTextToList('ki'));

    // Funktion zum Rendern der Trainingsdaten-Liste
    function renderTrainingData() {
        dataList.innerHTML = '';
        currentTrainingData.forEach((item, index) => {
            const li = document.createElement('li');
            const labelSpan = document.createElement('span');
            labelSpan.textContent = `[${item.label.toUpperCase()}]`;
            labelSpan.classList.add('label', item.label === 'ki' ? 'ki-label' : 'human-label');

            const textSpan = document.createElement('span');
            textSpan.textContent = item.text.substring(0, 100) + '...'; // Kürze den Text

            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = '🗑️';
            deleteBtn.classList.add('delete-btn');
            deleteBtn.addEventListener('click', () => {
                currentTrainingData.splice(index, 1);
                renderTrainingData();
            });

            li.appendChild(labelSpan);
            li.appendChild(textSpan);
            li.appendChild(deleteBtn);
            dataList.appendChild(li);
        });
    }

    // Funktion zum Speichern der Daten und erneutem Training des Modells
    saveDataBtn.addEventListener('click', async () => {
        saveDataBtn.disabled = true;
        saveDataBtn.textContent = 'Speichere...';
        saveStatusMsg.textContent = '';

        try {
            const response = await fetch(SAVE_DATA_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    password: passwordInput.value,
                    data: currentTrainingData
                })
            });

            const data = await response.json();

            if (response.ok) {
                saveStatusMsg.textContent = '✅ Daten gespeichert und Modell neu trainiert!';
                saveStatusMsg.style.color = '#28a745';
                console.log(data.message);
            } else {
                saveStatusMsg.textContent = `❌ Fehler: ${data.error}`;
                saveStatusMsg.style.color = '#dc3545';
                console.error(data.error);
            }
        } catch (error) {
            saveStatusMsg.textContent = '❌ Es gab ein Problem bei der Verbindung zum Server.';
            saveStatusMsg.style.color = '#dc3545';
            console.error('API-Anfrage fehlgeschlagen:', error);
        } finally {
            saveDataBtn.disabled = false;
            saveDataBtn.textContent = 'Speichern und Modell neu trainieren';
        }
    });

});