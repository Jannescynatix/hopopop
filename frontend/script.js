/* frontend/script.js */
document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('text-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    const menschBar = document.querySelector('.mensch-bar');
    const kiBar = document.querySelector('.ki-bar');
    const menschLabel = document.getElementById('mensch-label');
    const kiLabel = document.getElementById('ki-label');

    const adminPasswordInput = document.getElementById('admin-password-input');
    const passwordSubmitBtn = document.getElementById('password-submit-btn');
    const loginForm = document.getElementById('login-form');
    const loginErrorMsg = document.getElementById('login-error-msg');
    const trainingDataView = document.getElementById('training-data-view');
    const dataList = document.getElementById('data-list');
    const newTextInput = document.getElementById('new-text-input');
    const addHumanBtn = document.getElementById('add-human-btn');
    const addKiBtn = document.getElementById('add-ki-btn');
    const saveStatusMsg = document.getElementById('save-status-msg');
    const retrainBtn = document.getElementById('retrain-btn');
    const retrainStatusMsg = document.getElementById('retrain-status-msg');
    const refreshStatsBtn = document.getElementById('refresh-stats-btn');

    const navLinks = document.querySelectorAll('.nav-link');
    const pageSections = document.querySelectorAll('.page-section');
    const burgerMenu = document.getElementById('burger-menu');
    const navMenu = document.querySelector('.nav-menu');

    let adminToken = null;

    // Feste Werte für die Startseiten-Statistiken
    const FRONTEND_STATS = {
        total_words: 1000000,
        total_texts: 15000,
        human_texts: 7500,
        ki_texts: 7500
    };

    // Funktion zur Anzeige von Toast-Nachrichten
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast-message toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }

    // Funktion zur Navigation
    function navigateTo(targetId) {
        pageSections.forEach(section => {
            section.classList.remove('active');
            section.classList.add('hidden');
        });
        const targetSection = document.getElementById(targetId);
        if (targetSection) {
            targetSection.classList.remove('hidden');
            targetSection.classList.add('active');
        }
    }

    // Navigation-Logik
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.target.getAttribute('data-target');
            navigateTo(targetId);

            // Setzt den aktiven Link
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Schließt das mobile Menü
            navMenu.classList.remove('active');
            burgerMenu.classList.remove('active');
        });
    });

    // Burger-Menü-Logik
    burgerMenu.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        burgerMenu.classList.toggle('active');
    });

    // Haupt-Funktion für die Analyse
    analyzeBtn.addEventListener('click', async () => {
        const text = textInput.value;
        if (!text) {
            showToast('Bitte geben Sie einen Text ein.', 'warning');
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:5000/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text })
            });

            const data = await response.json();

            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            const menschProb = data.menschlich;
            const kiProb = data.ki;

            resultContainer.classList.remove('hidden');
            resultText.textContent = `Wahrscheinlichkeit: Menschlich: ${menschProb.toFixed(2)}% | KI: ${kiProb.toFixed(2)}%`;
            menschBar.style.width = `${menschProb}%`;
            kiBar.style.width = `${kiProb}%`;
            menschLabel.textContent = `${menschProb.toFixed(2)}%`;
            kiLabel.textContent = `${kiProb.toFixed(2)}%`;

        } catch (error) {
            console.error('Fehler:', error);
            showToast('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error');
        }
    });

    // Funktion zum Abrufen und Anzeigen der Daten
    const fetchDataAndDisplay = async (token) => {
        try {
            const response = await fetch('http://127.0.0.1:5000/get_data_status', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            const data = await response.json();

            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            // Aktualisiere Admin-Panel Statistiken
            document.getElementById('human-count').textContent = data.data.filter(d => d.label === 'menschlich').length;
            document.getElementById('ki-count').textContent = data.data.filter(d => d.label === 'ki').length;
            document.getElementById('untrainiert-count').textContent = data.data.filter(d => d.trained === false).length;
            document.getElementById('total-words').textContent = data.stats.word_counts.total.toLocaleString('de-DE');

            document.getElementById('human-word-count').textContent = data.stats.word_counts.menschlich.toLocaleString('de-DE');
            document.getElementById('human-char-count').textContent = data.stats.char_counts.menschlich.toLocaleString('de-DE');
            document.getElementById('ki-word-count').textContent = data.stats.word_counts.ki.toLocaleString('de-DE');
            document.getElementById('ki-char-count').textContent = data.stats.char_counts.ki.toLocaleString('de-DE');
            document.getElementById('total-word-count').textContent = data.stats.word_counts.total.toLocaleString('de-DE');
            document.getElementById('total-char-count').textContent = data.stats.char_counts.total.toLocaleString('de-DE');
            document.getElementById('avg-human-length').textContent = data.stats.avg_lengths.menschlich.toFixed(2);
            document.getElementById('avg-ki-length').textContent = data.stats.avg_lengths.ki.toFixed(2);

            const frequentHumanList = document.getElementById('frequent-human-words');
            const frequentKiList = document.getElementById('frequent-ki-words');
            const frequentTotalList = document.getElementById('frequent-total-words');

            frequentHumanList.innerHTML = data.stats.frequent_words.menschlich.map(item => `<li>${item[0]} (${item[1]})</li>`).join('');
            frequentKiList.innerHTML = data.stats.frequent_words.ki.map(item => `<li>${item[0]} (${item[1]})</li>`).join('');
            frequentTotalList.innerHTML = data.stats.frequent_words.total.map(item => `<li>${item[0]} (${item[1]})</li>`).join('');

            dataList.innerHTML = '';
            data.data.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span class="data-text ${item.trained ? '' : 'untrained-text'}">${item.text}</span>
                    <span class="data-label">${item.label}</span>
                    <div class="data-actions">
                        <button class="delete-btn" data-text="${item.text}"><i class="fas fa-trash"></i></button>
                    </div>
                `;
                dataList.appendChild(li);
            });

        } catch (error) {
            console.error('Fehler beim Abrufen der Daten:', error);
            showToast('Fehler beim Laden der Admin-Daten.', 'error');
        }
    };

    // Admin-Login-Logik
    passwordSubmitBtn.addEventListener('click', async () => {
        const password = adminPasswordInput.value;
        if (!password) {
            loginErrorMsg.textContent = 'Bitte Passwort eingeben.';
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:5000/admin_login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ password })
            });

            const data = await response.json();

            if (response.ok) {
                adminToken = data.token;
                loginForm.classList.add('hidden');
                trainingDataView.classList.remove('hidden');
                fetchDataAndDisplay(adminToken);
                showToast('Login erfolgreich!', 'success');
            } else {
                loginErrorMsg.textContent = data.error;
            }
        } catch (error) {
            console.error('Fehler:', error);
            loginErrorMsg.textContent = 'Verbindungsfehler.';
        }
    });

    // Daten hinzufügen
    const handleAddData = async (label) => {
        const text = newTextInput.value;
        if (!text) {
            showToast('Bitte geben Sie einen Text zum Hinzufügen ein.', 'warning');
            return;
        }

        if (!adminToken) {
            showToast('Sitzung abgelaufen. Bitte neu einloggen.', 'warning');
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:5000/add_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${adminToken}`
                },
                body: JSON.stringify({ text, label })
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.message, 'success');
                newTextInput.value = '';
                fetchDataAndDisplay(adminToken);
            } else {
                showToast(data.error, 'error');
            }
        } catch (error) {
            showToast('Fehler beim Hinzufügen der Daten.', 'error');
        }
    };

    addHumanBtn.addEventListener('click', () => handleAddData('menschlich'));
    addKiBtn.addEventListener('click', () => handleAddData('ki'));

    // Daten löschen
    dataList.addEventListener('click', async (e) => {
        if (e.target.closest('.delete-btn')) {
            const deleteBtn = e.target.closest('.delete-btn');
            const textToDelete = deleteBtn.getAttribute('data-text');
            if (!adminToken) {
                showToast('Sitzung abgelaufen. Bitte neu einloggen.', 'warning');
                return;
            }

            try {
                const response = await fetch('http://127.0.0.1:5000/delete_data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${adminToken}`
                    },
                    body: JSON.stringify({ text: textToDelete })
                });
                const data = await response.json();
                if (response.ok) {
                    showToast(data.message, 'success');
                    fetchDataAndDisplay(adminToken);
                } else {
                    showToast(data.error, 'error');
                }
            } catch (error) {
                showToast('Fehler beim Löschen der Daten.', 'error');
            }
        }
    });

    // Modell neu trainieren
    retrainBtn.addEventListener('click', async () => {
        if (!adminToken) {
            showToast('Sitzung abgelaufen. Bitte neu einloggen.', 'warning');
            return;
        }

        showToast('Modelltraining gestartet. Dies kann einen Moment dauern.', 'info');
        retrainStatusMsg.textContent = 'Training läuft...';
        retrainBtn.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:5000/retrain_model', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${adminToken}`
                }
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.message, 'success');
                retrainStatusMsg.textContent = 'Training abgeschlossen!';
                fetchDataAndDisplay(adminToken);
            } else {
                showToast(data.error, 'error');
                retrainStatusMsg.textContent = `Fehler: ${data.error}`;
            }
        } catch (error) {
            showToast('Fehler beim Neu-Trainieren.', 'error');
            retrainStatusMsg.textContent = 'Fehler beim Neu-Trainieren.';
        } finally {
            retrainBtn.disabled = false;
        }
    });

    // Statistiken aktualisieren
    if (refreshStatsBtn) {
        refreshStatsBtn.addEventListener('click', () => {
            if (adminToken) {
                fetchDataAndDisplay(adminToken);
                showToast('Statistiken aktualisiert.', 'info');
            } else {
                showToast('Bitte loggen Sie sich ein, um Statistiken zu aktualisieren.', 'warning');
            }
        });
    }

    // Scroll-Animationen
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    animateElements.forEach(el => observer.observe(el));

    // Hardcode-Werte für die Startseite einfügen
    document.getElementById('total-word-count-front').textContent = (FRONTEND_STATS.total_words).toLocaleString('de-DE');
    document.getElementById('total-text-count-front').textContent = (FRONTEND_STATS.total_texts).toLocaleString('de-DE');
    document.getElementById('human-text-count-front').textContent = (FRONTEND_STATS.human_texts).toLocaleString('de-DE');
    document.getElementById('ki-text-count-front').textContent = (FRONTEND_STATS.ki_texts).toLocaleString('de-DE');
});