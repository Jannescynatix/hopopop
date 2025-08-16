// frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Navigations-Elemente
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page-section');
    const body = document.body;

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
    const humanCountSpan = document.getElementById('human-count');
    const kiCountSpan = document.getElementById('ki-count');
    const untrainiertCountSpan = document.getElementById('untrainiert-count');
    const retrainBtn = document.getElementById('retrain-btn');

    // WICHTIG: Ersetzen Sie DIESE URL durch die URL Ihrer gehosteten Render-App
    const API_BASE_URL = 'https://b-kb9u.onrender.com';
    let currentTrainingData = [];

    // --- Allgemeine Hilfsfunktion für Toast-Nachrichten ---
    function showToast(message, type = 'info', duration = 3000) {
        // Entferne alte Toasts, falls vorhanden
        const existingToast = document.querySelector('.toast-message');
        if (existingToast) existingToast.remove();

        const toast = document.createElement('div');
        toast.className = `toast-message toast-${type}`;
        toast.textContent = message;
        body.appendChild(toast);

        // Zeige den Toast an
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // Verstecke und entferne den Toast nach der Dauer
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300); // Warte auf Fade-out
        }, duration);
    }

    // --- Navigations-Logik ---
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.target.dataset.target;

            pages.forEach(page => page.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            navLinks.forEach(navLink => navLink.classList.remove('active'));
            link.classList.add('active');

            if (targetId === 'admin-panel' && !loginForm.classList.contains('hidden')) {
                updateTrainingDataStatus();
            }
        });
    });

    // --- Haupt-App-Logik ---
    analyzeBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();

        if (text.length === 0) {
            showToast('Bitte Text eingeben.', 'error');
            return;
        }

        resultContainer.classList.add('hidden');
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analysiere...';

        try {
            showToast('Text wird analysiert...', 'info', 2000);
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
                    showToast('Die Analyse ist abgeschlossen.', 'warning');
                } else {
                    resultText.textContent = `Dieser Text wurde wahrscheinlich von einem Menschen geschrieben.`;
                    showToast('Die Analyse ist abgeschlossen.', 'success');
                }

                kiBar.style.width = `${kiProb}%`;
                menschBar.style.width = `${menschProb}%`;
                kiLabel.textContent = `KI: ${kiProb}%`;
                menschLabel.textContent = `Menschlich: ${menschProb}%`;
            } else {
                showToast(`Fehler bei der Analyse: ${data.error}`, 'error');
                resultText.textContent = `Fehler: ${data.error}`;
            }
        } catch (error) {
            console.error('Fehler bei der API-Anfrage:', error);
            showToast('Verbindungsproblem zur API.', 'error');
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
            showToast('Bitte Passwort eingeben.', 'error');
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
                showToast('Login erfolgreich!', 'success');
            } else {
                loginErrorMsg.textContent = data.error || 'Login fehlgeschlagen.';
                showToast(`Login fehlgeschlagen: ${data.error}`, 'error');
            }
        } catch (error) {
            loginErrorMsg.textContent = 'Verbindungsfehler zur API.';
            console.error(error);
            showToast('Verbindungsproblem zur API.', 'error');
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
            showToast('Bitte Text eingeben.', 'error');
            return;
        }

        showToast('Füge Daten hinzu...', 'info');
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
                currentTrainingData.push({ text, label, trained: false });
                newTextInput.value = '';
                renderTrainingData();
                showToast('✅ Daten erfolgreich zur Warteschlange hinzugefügt!', 'success');
            } else {
                showToast(`❌ Fehler: ${data.error}`, 'error');
            }
        } catch (error) {
            showToast('❌ Verbindungsproblem beim Hinzufügen.', 'error');
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
        showToast('Lösche Daten...', 'info');

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
                showToast('✅ Daten erfolgreich gelöscht!', 'success');
            } else {
                showToast(`❌ Fehler: ${data.error}`, 'error');
            }
        } catch (error) {
            showToast('❌ Verbindungsproblem beim Löschen.', 'error');
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
        showToast('Modell-Training gestartet...', 'info');
        retrainBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/retrain_model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password })
            });

            const data = await response.json();

            if (response.ok) {
                showToast('✅ Modell-Training gestartet. Schau in die Logs für Details!', 'success', 5000);
                setTimeout(updateTrainingDataStatus, 3000); // Warte 3s, bis DB-Update
            } else {
                showToast(`❌ Fehler: ${data.error}`, 'error');
            }
        } catch (error) {
            showToast('❌ Verbindungsproblem beim Training.', 'error');
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
                showToast(`Fehler beim Aktualisieren des Datenstatus: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error("Fehler beim Abrufen der Daten:", error);
            showToast('Verbindungsproblem beim Abrufen des Datenstatus.', 'error');
        }
    }
});