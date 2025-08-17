// frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Navigations-Elemente
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page-section');
    const body = document.body;
    const burgerMenu = document.getElementById('burger-menu');
    const navMenu = document.querySelector('.nav-menu');

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
    const totalWordsSpan = document.getElementById('total-words');
    const retrainBtn = document.getElementById('retrain-btn');

    // NEUE Admin-Statistik-Elemente
    const totalWordsAllSpan = document.getElementById('total-words-all');
    const totalCharsAllSpan = document.getElementById('total-chars-all');
    const totalSentencesAllSpan = document.getElementById('total-sentences-all');
    const humanWordsSpan = document.getElementById('human-words');
    const humanCharsSpan = document.getElementById('human-chars');
    const kiWordsSpan = document.getElementById('ki-words');
    const kiCharsSpan = document.getElementById('ki-chars');
    const kiWordsList = document.getElementById('ki-words-list');
    const humanWordsList = document.getElementById('human-words-list');
    const allWordsList = document.getElementById('all-words-list');

    // WICHTIG: Ersetzen Sie DIESE URL durch die URL Ihrer gehosteten Render-App
    const API_BASE_URL = 'https://b-kb9u.onrender.com';
    let currentTrainingData = [];
    let adminToken = localStorage.getItem('adminToken') || null;

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
    burgerMenu.addEventListener('click', () => {
        navMenu.classList.toggle('active');
    });

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.target.dataset.target;

            // Schließe das Menü bei Klick (für mobile Ansicht)
            navMenu.classList.remove('active');

            pages.forEach(page => page.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            navLinks.forEach(navLink => navLink.classList.remove('active'));
            link.classList.add('active');

            if (targetId === 'admin-panel') {
                checkAdminSession();
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
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analysiere...';

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
    async function checkAdminSession() {
        if (adminToken) {
            // Versuche, mit dem gespeicherten Token Daten abzurufen
            const response = await fetch(`${API_BASE_URL}/get_data_status`, {
                headers: { 'Authorization': `Bearer ${adminToken}` }
            });

            if (response.ok) {
                const data = await response.json();
                currentTrainingData = data.data;
                renderTrainingData(data.word_counts);
                await fetchAndRenderStats(); // Neu: Statistiken abrufen und anzeigen
                loginForm.classList.add('hidden');
                trainingDataView.classList.remove('hidden');
                return;
            }
        }
        // Zeige Login-Formular, wenn kein Token oder ungültig
        loginForm.classList.remove('hidden');
        trainingDataView.classList.add('hidden');
    }

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
                adminToken = data.token;
                localStorage.setItem('adminToken', adminToken);
                currentTrainingData = data.data;
                renderTrainingData(data.word_counts);
                await fetchAndRenderStats(); // Neu: Statistiken abrufen und anzeigen
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
        if (!text) {
            showToast('Bitte Text eingeben.', 'error');
            return;
        }
        if (!adminToken) {
            showToast('Fehler: Nicht angemeldet.', 'error');
            checkAdminSession();
            return;
        }

        showToast('Füge Daten hinzu...', 'info');
        addHumanBtn.disabled = true;
        addKiBtn.disabled = true;
        try {
            const response = await fetch(`${API_BASE_URL}/add_data`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${adminToken}`
                },
                body: JSON.stringify({ text, label })
            });

            const data = await response.json();

            if (response.ok) {
                currentTrainingData.push({ text, label, trained: false });
                newTextInput.value = '';
                await updateTrainingDataStatus();
                await fetchAndRenderStats(); // Neu: Statistiken aktualisieren
                showToast('✅ Daten erfolgreich zur Warteschlange hinzugefügt!', 'success');
            } else {
                showToast(`❌ Fehler: ${data.error}`, 'error');
                if (response.status === 401) {
                    adminToken = null;
                    localStorage.removeItem('adminToken');
                    checkAdminSession();
                }
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
        if (!adminToken) {
            showToast('Fehler: Nicht angemeldet.', 'error');
            checkAdminSession();
            return;
        }

        showToast('Lösche Daten...', 'info');
        try {
            const response = await fetch(`${API_BASE_URL}/delete_data`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${adminToken}`
                },
                body: JSON.stringify({ text })
            });

            const data = await response.json();

            if (response.ok) {
                currentTrainingData.splice(index, 1);
                await updateTrainingDataStatus();
                await fetchAndRenderStats(); // Neu: Statistiken aktualisieren
                showToast('✅ Daten erfolgreich gelöscht!', 'success');
            } else {
                showToast(`❌ Fehler: ${data.error}`, 'error');
                if (response.status === 401) {
                    adminToken = null;
                    localStorage.removeItem('adminToken');
                    checkAdminSession();
                }
            }
        } catch (error) {
            showToast('❌ Verbindungsproblem beim Löschen.', 'error');
        }
    }

    // Funktion zum Rendern der Trainingsdaten-Liste
    function renderTrainingData(wordCounts) {
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
        if (wordCounts) {
            totalWordsSpan.textContent = wordCounts.total;
        }
    }

    // NEUE Funktion: Ruft Statistiken ab und rendert sie
    async function fetchAndRenderStats() {
        if (!adminToken) {
            console.log("Nicht angemeldet, kann Statistiken nicht abrufen.");
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/get_stats`, {
                headers: { 'Authorization': `Bearer ${adminToken}` }
            });
            const data = await response.json();

            if (response.ok) {
                // Gesamtstatistiken
                totalWordsAllSpan.textContent = data.total_words;
                totalCharsAllSpan.textContent = data.total_chars;
                totalSentencesAllSpan.textContent = data.total_sentences;

                // Kategorienspezifische Statistiken
                humanWordsSpan.textContent = data.human.word_count;
                humanCharsSpan.textContent = data.human.char_count;
                kiWordsSpan.textContent = data.ki.word_count;
                kiCharsSpan.textContent = data.ki.char_count;

                // Häufigste Wörter Listen
                renderWordList(kiWordsList, data.ki.frequent_words);
                renderWordList(humanWordsList, data.human.frequent_words);
                renderWordList(allWordsList, data.total_frequent_words);

            } else {
                console.error("Fehler beim Abrufen der Statistiken:", data.error);
                showToast(`Fehler beim Abrufen der Statistiken: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error("Fehler bei der API-Anfrage für Statistiken:", error);
            showToast('Verbindungsproblem beim Abrufen der Statistiken.', 'error');
        }
    }

    // NEUE Funktion: Rendert eine Liste von Wörtern in ein <ul> oder <ol> Element
    function renderWordList(element, wordList) {
        element.innerHTML = '';
        wordList.forEach(([word, count]) => {
            const li = document.createElement('li');
            li.textContent = `${word} (${count})`;
            element.appendChild(li);
        });
    }

    // Funktion zum Neu-Trainieren des Modells
    retrainBtn.addEventListener('click', async () => {
        if (!adminToken) {
            showToast('Fehler: Nicht angemeldet.', 'error');
            checkAdminSession();
            return;
        }
        showToast('Modell-Training gestartet...', 'info');
        retrainBtn.disabled = true;
        retrainBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Trainiere...';
        try {
            const response = await fetch(`${API_BASE_URL}/retrain_model`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${adminToken}`
                }
            });
            const data = await response.json();
            if (response.ok) {
                showToast('✅ Modell-Training gestartet. Schau in die Logs für Details!', 'success', 5000);
                setTimeout(updateTrainingDataStatus, 3000); // Warte 3s, bis DB-Update
            } else {
                showToast(`❌ Fehler: ${data.error}`, 'error');
                if (response.status === 401) {
                    adminToken = null;
                    localStorage.removeItem('adminToken');
                    checkAdminSession();
                }
            }
        } catch (error) {
            showToast('❌ Verbindungsproblem beim Training.', 'error');
        } finally {
            retrainBtn.disabled = false;
            retrainBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Modell neu trainieren';
        }
    });

    async function updateTrainingDataStatus() {
        if (!adminToken) {
            console.log("Nicht angemeldet, kann Datenstatus nicht aktualisieren.");
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/get_data_status`, {
                headers: { 'Authorization': `Bearer ${adminToken}` }
            });

            const data = await response.json();
            if (response.ok) {
                currentTrainingData = data.data;
                renderTrainingData(data.word_counts);
            } else {
                console.error("Fehler beim Abrufen der Daten:", data.error);
                showToast(`Fehler beim Aktualisieren des Datenstatus: ${data.error}`, 'error');
                if (response.status === 401) {
                    adminToken = null;
                    localStorage.removeItem('adminToken');
                    checkAdminSession();
                }
            }
        } catch (error) {
            console.error("Fehler beim Abrufen der Daten:", error);
            showToast('Verbindungsproblem beim Abrufen des Datenstatus.', 'error');
        }
    }

    // Initialen Check beim Laden der Seite
    if (document.getElementById('admin-panel').classList.contains('active')) {
        checkAdminSession();
    }
});