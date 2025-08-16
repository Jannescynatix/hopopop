// frontend/tracker.js
document.addEventListener('DOMContentLoaded', () => {
    // WICHTIG: Ersetze DIESE URL durch die URL deines Node.js-Analytics-Servers
    const ANALYTICS_API_URL = 'https://monadminserver.onrender.com';

    // Hilfsfunktion zum Senden von Daten an den Server
    const sendLog = async (event, details = {}) => {
        try {
            await fetch(`${ANALYTICS_API_URL}/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ event, details })
            });
        } catch (error) {
            console.error('Fehler beim Senden des Analytics-Protokolls:', error);
        }
    };

    // --- Logge den Seitenaufruf ---
    const logPageView = () => {
        const userAgent = navigator.userAgent;
        let device = 'Desktop';
        if (/(Mobi|Android|iPhone|iPad|iPod)/.test(userAgent)) {
            device = 'Mobile';
        }

        sendLog('page_view', {
            browser: userAgent,
            device: device,
            url: window.location.href,
        });
    };
    logPageView();

    // --- Logge das Admin-Panel Login & Aktionen ---
    const originalFetch = window.fetch;
    window.fetch = async (url, options) => {
        const response = await originalFetch(url, options);

        if (url.includes('/admin_login') && options.method === 'POST') {
            const data = await response.clone().json();
            if (data.message === 'Login erfolgreich') {
                sendLog('admin_login_success', {
                    username: options.body.username
                });
            } else {
                sendLog('admin_login_failure', {
                    username: options.body.username
                });
            }
        }

        if (url.includes('/add_data') && options.method === 'POST') {
            sendLog('data_added', {
                label: JSON.parse(options.body).label
            });
        }

        if (url.includes('/delete_data') && options.method === 'POST') {
            sendLog('data_deleted', {
                text: JSON.parse(options.body).text.substring(0, 50) + '...'
            });
        }

        return response;
    };
});

// --- So bindest du andere Buttons ein ---
// Beispiel: Logge Klicks auf den Analyse-Button
const analyzeBtn = document.getElementById('analyze-btn');
if (analyzeBtn) {
    analyzeBtn.addEventListener('click', () => {
        sendLog('button_click', { button: 'analyze-btn' });
    });
}