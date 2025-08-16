// frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Navigations-Elemente
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page-section');

    // App-Elemente
    const analyzeBtn = document.getElementById('analyze-btn');
    const textInput = document.getElementById('text-input');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    const kiBar = document.querySelector('.ki-bar');
    const menschBar = document.querySelector('.mensch-bar');
    const kiLabel = document.getElementById('ki-label');
    const menschLabel = document.getElementById('mensch-label');

    // Admin-Panel-Elemente
    const loginForm = document.getElementById('login-form');
    const passwordInput = document.getElementById('admin-password-input');
    const passwordSubmitBtn = document.getElementById('password-submit-btn');
    const loginErrorMsg = document.getElementById('login-error-msg');
    const trainingDataView = document.getElementById('training-data-view');
    const newTextInput = document.getElementById('new-text-input');
    const addHumanBtn = document.getElementById('add-human-btn');
    const addKiBtn = document.getElementById('add-ki-btn');
    const dataList = document.getElementById('data-list');
    const saveStatusMsg = document.getElementById('save-status-msg');
    const humanCountSpan = document.getElementById('human-count');
    const kiCountSpan = document.getElementById('ki-count');
    const untrainiertCountSpan = document.getElementById('untrainiert-count');
    const retrainBtn = document.getElementById('retrain-btn');
    const retrainStatusMsg = document.getElementById('retrain-status-msg');

    // WICHTIG: Ersetzen Sie DIESE URL durch die URL Ihrer gehosteten Render-App
    const API_BASE_URL = 'https://b-kb9u.onrender.com';
    let currentTrainingData = [];

    // --- Navigations-Logik ---
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.target.dataset.target;

            pages.forEach(page => page.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            navLinks.forEach(navLink => navLink.classList.remove('active'));
            link.classList.add('active');

            // Bei Wechsel zum Admin-Panel, Datenstatus aktualisieren
            if (targetId === 'admin-panel' && !loginForm.classList.contains('hidden')) {
                updateTrainingDataStatus();
            }
        });
    });

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
            const response = await fetch(`${API_BASE_URL}/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });

            const data = await response.json();

            if (response.ok) {
                const kiProb = data.ki;
                const menschProb = data.menschlich;

                resultContainer.classList.remove('hidden');
                if (kiProb > menschProb) {
                    resultText.textContent = `Dieser Text wurde wahrscheinlich von einer KI generiert.`;
                } else {
                    resultText.textContent = `Dieser Text wurde wahrscheinlich von einem Menschen geschrieben.`;
                }
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
            analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analysieren';
        }
    });

    // --- Admin-Logik ---
    passwordSubmitBtn.addEventListener('click', async () => {
        const password = passwordInput.value;
        if (!password) {
            loginErrorMsg.textContent = 'Bitte Passwort eingeben.';
            return;
        }

        passwordSubmitBtn.disabled = true;
        passwordSubmitBtn.textContent = 'Logge ein...';
        loginErrorMsg.textContent = '';

        try {
            const response = await fetch(`${API_BASE_URL}/admin_login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password })
            });

            const data = await response.json();

            if (response.ok) {
                currentTrainingData = data.data;
                renderTrainingData();
                loginForm.classList.add('hidden');
                trainingDataView.classList.remove('hidden');
            } else {
                loginErrorMsg.textContent = data.error || 'Login fehlgeschlagen.';
            }
        } catch (error) {
            loginErrorMsg.textContent = 'Verbindungsfehler zur API.';
            console.error(error);
        } finally {
            passwordSubmitBtn.disabled = false;
            passwordSubmitBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
        }
    });

    // Funktion zum Hinzufügen von Texten
    async function addTextToList(label) {
        const text = newTextInput.value.trim();
        const password = passwordInput.value;
        if (!text) {
            saveStatusMsg.textContent = 'Bitte Text eingeben.';
            saveStatusMsg.style.color = '#dc3545';
            return;
        }

        saveStatusMsg.textContent = 'Füge hinzu...';
        saveStatusMsg.style.color = '#007bff';
        addHumanBtn.disabled = true;
        addKiBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/add_data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, label, password })
            });

            const data = await response.json();

            if (response.ok) {
                // Füge das neue Element zur lokalen Liste hinzu, markiert als 'untrained'
                currentTrainingData.push({ text, label, trained: false });
                newTextInput.value = '';
                renderTrainingData();
                saveStatusMsg.textContent = '✅ Daten erfolgreich zur Warteschlange hinzugefügt! Modell neu trainieren, um sie zu verwenden.';
                saveStatusMsg.style.color = '#28a745';
            } else {
                saveStatusMsg.textContent = `❌ Fehler: ${data.error}`;
                saveStatusMsg.style.color = '#dc3545';
            }
        } catch (error) {
            saveStatusMsg.textContent = '❌ Verbindungsproblem beim Hinzufügen.';
            saveStatusMsg.style.color = '#dc3545';
        } finally {
            addHumanBtn.disabled = false;
            addKiBtn.disabled = false;
        }
    }

    addHumanBtn.addEventListener('click', () => addTextToList('menschlich'));
    addKiBtn.addEventListener('click', () => addTextToList('ki'));

    // Funktion zum Löschen eines Texts
    async function deleteText(text, index) {
        const password = passwordInput.value;

        saveStatusMsg.textContent = 'Lösche...';
        saveStatusMsg.style.color = '#007bff';

        try {
            const response = await fetch(`${API_BASE_URL}/delete_data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, password })
            });

            const data = await response.json();

            if (response.ok) {
                currentTrainingData.splice(index, 1);
                renderTrainingData();
                saveStatusMsg.textContent = '✅ Daten erfolgreich gelöscht!';
                saveStatusMsg.style.color = '#28a745';
            } else {
                saveStatusMsg.textContent = `❌ Fehler: ${data.error}`;
                saveStatusMsg.style.color = '#dc3545';
            }
        } catch (error) {
            saveStatusMsg.textContent = '❌ Verbindungsproblem beim Löschen.';
            saveStatusMsg.style.color = '#dc3545';
        }
    }

    // Funktion zum Rendern der Trainingsdaten-Liste
    function renderTrainingData() {
        dataList.innerHTML = '';
        let humanCount = 0;
        let kiCount = 0;
        let untrainedCount = 0;

        currentTrainingData.forEach((item, index) => {
            if (item.label === 'menschlich') humanCount++;
            else kiCount++;

            if (!item.trained) untrainedCount++;

            const li = document.createElement('li');
            li.innerHTML = `
                <span class="data-text ${item.trained ? '' : 'untrained-text'}">${item.text}</span>
                <span class="data-actions">
                    <span class="label ${item.label === 'ki' ? 'ki-label' : 'human-label'}">
                        ${item.label.toUpperCase()}
                    </span>
                    <button class="delete-btn" data-text="${item.text}"><i class="fas fa-trash-alt"></i></button>
                </span>
            `;
            dataList.appendChild(li);

            const deleteBtn = li.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', () => deleteText(item.text, index));
        });

        humanCountSpan.textContent = humanCount;
        kiCountSpan.textContent = kiCount;
        untrainiertCountSpan.textContent = untrainedCount;
    }

    // Funktion zum Neu-Trainieren des Modells
    retrainBtn.addEventListener('click', async () => {
        const password = passwordInput.value;
        retrainStatusMsg.textContent = 'Modell wird neu trainiert...';
        retrainStatusMsg.style.color = '#007bff';
        retrainBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/retrain_model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password })
            });

            const data = await response.json();

            if (response.ok) {
                retrainStatusMsg.textContent = '✅ Modell-Training gestartet. Dies kann einen Moment dauern.';
                retrainStatusMsg.style.color = '#28a745';
                // Aktualisiere den Datenstatus, um die 'trained' Flagge zu sehen
                setTimeout(updateTrainingDataStatus, 3000); // 3 Sekunden warten
            } else {
                retrainStatusMsg.textContent = `❌ Fehler: ${data.error}`;
                retrainStatusMsg.style.color = '#dc3545';
            }
        } catch (error) {
            retrainStatusMsg.textContent = '❌ Verbindungsproblem beim Training.';
            retrainStatusMsg.style.color = '#dc3545';
        } finally {
            retrainBtn.disabled = false;
        }
    });

    async function updateTrainingDataStatus() {
        const password = passwordInput.value;
        try {
            const response = await fetch(`${API_BASE_URL}/get_data_status?password=${password}`);
            const data = await response.json();
            if (response.ok) {
                currentTrainingData = data.data;
                renderTrainingData();
            } else {
                console.error("Fehler beim Abrufen der Daten:", data.error);
            }
        } catch (error) {
            console.error("Fehler beim Abrufen der Daten:", error);
        }
    }
});