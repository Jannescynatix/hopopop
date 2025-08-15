// frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyze-btn');
    const textInput = document.getElementById('text-input');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    const kiBar = document.querySelector('.ki-bar');
    const menschBar = document.querySelector('.mensch-bar');
    const kiLabel = document.getElementById('ki-label');
    const menschLabel = document.getElementById('mensch-label');

    const addTextInput = document.getElementById('add-text-input');
    const addKiBtn = document.getElementById('add-ki-btn');
    const addMenschBtn = document.getElementById('add-mensch-btn');
    const menschlichList = document.getElementById('menschlich-list');
    const kiList = document.getElementById('ki-list');

    // **WICHTIG:** URL Ihrer gehosteten Render-App
    const API_BASE_URL = 'https://ihre-ki-detektor-app.onrender.com';

    // Funktion zum Abrufen und Anzeigen der Trainingsdaten
    const fetchAndDisplayData = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/data`);
            const data = await response.json();

            menschlichList.innerHTML = '';
            kiList.innerHTML = '';

            data.menschlich.forEach(text => {
                const li = document.createElement('li');
                li.textContent = text.slice(0, 50) + '...'; // Zeige nur einen Ausschnitt
                const deleteBtn = document.createElement('button');
                deleteBtn.textContent = 'x';
                deleteBtn.onclick = () => deleteText(text, 'menschlich');
                li.appendChild(deleteBtn);
                menschlichList.appendChild(li);
            });

            data.ki.forEach(text => {
                const li = document.createElement('li');
                li.textContent = text.slice(0, 50) + '...';
                const deleteBtn = document.createElement('button');
                deleteBtn.textContent = 'x';
                deleteBtn.onclick = () => deleteText(text, 'ki');
                li.appendChild(deleteBtn);
                kiList.appendChild(li);
            });
        } catch (error) {
            console.error('Fehler beim Laden der Trainingsdaten:', error);
        }
    };

    // Funktion zum Löschen von Texten
    const deleteText = async (text, label) => {
        const confirmDelete = confirm('Sind Sie sicher, dass Sie diesen Text löschen möchten? Das Modell wird neu trainiert.');
        if (!confirmDelete) return;

        try {
            const response = await fetch(`${API_BASE_URL}/delete_text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, label })
            });
            const data = await response.json();
            alert(data.message);
            fetchAndDisplayData();
        } catch (error) {
            console.error('Fehler beim Löschen des Textes:', error);
            alert('Fehler beim Löschen des Textes.');
        }
    };

    // Initialen Daten laden
    fetchAndDisplayData();

    // Event-Listener für Analyse-Button
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
            analyzeBtn.textContent = 'Analysieren';
        }
    });

    // Event-Listener für Hinzufügen-Buttons
    const handleAddText = async (label) => {
        const text = addTextInput.value.trim();
        if (text.length === 0) {
            alert('Bitte geben Sie einen Text ein.');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/add_text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, label })
            });
            const data = await response.json();
            alert(data.message);
            addTextInput.value = '';
            fetchAndDisplayData();
        } catch (error) {
            console.error('Fehler beim Hinzufügen des Textes:', error);
            alert('Fehler beim Hinzufügen des Textes.');
        }
    };

    addKiBtn.addEventListener('click', () => handleAddText('ki'));
    addMenschBtn.addEventListener('click', () => handleAddText('menschlich'));

});