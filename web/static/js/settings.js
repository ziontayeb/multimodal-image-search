// Load settings on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    loadConfigInfo();
});

// Load current settings
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) {
            throw new Error('Failed to load settings');
        }

        const data = await response.json();

        // Populate form fields
        document.getElementById('pineconeKey').value = data.PINECONE_API_KEY || '';
        document.getElementById('indexName').value = data.INDEX_NAME || '';
        document.getElementById('pineconeCloud').value = data.PINECONE_CLOUD || 'aws';
        document.getElementById('pineconeRegion').value = data.PINECONE_REGION || '';
        document.getElementById('geminiKey').value = data.GEMINI_API_KEY || '';
        document.getElementById('geminiModel').value = data.GEMINI_MODEL || '';
        document.getElementById('clipModel').value = data.CLIP_MODEL || '';
        document.getElementById('reduceDim').value = data.REDUCE_DIM || '384';

    } catch (error) {
        showStatus('Failed to load settings: ' + error.message, 'error');
    }
}

// Load configuration info
async function loadConfigInfo() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }

        const data = await response.json();
        const configEl = document.getElementById('configInfo');

        configEl.innerHTML = `
            <p><strong>Pinecone Index:</strong> ${data.INDEX_NAME || 'Not set'}</p>
            <p><strong>Cloud Provider:</strong> ${data.PINECONE_CLOUD || 'Not set'}</p>
            <p><strong>Region:</strong> ${data.PINECONE_REGION || 'Not set'}</p>
            <p><strong>Gemini Model:</strong> ${data.GEMINI_MODEL || 'Not set'}</p>
            <p><strong>CLIP Model:</strong> ${data.CLIP_MODEL || 'Not set'}</p>
            <p><strong>Dimension:</strong> ${data.REDUCE_DIM || 'Not set'}</p>
            <p><strong>Pinecone API Key:</strong> ${data.PINECONE_API_KEY ? '***' + data.PINECONE_API_KEY.slice(-4) : 'Not set'}</p>
            <p><strong>Gemini API Key:</strong> ${data.GEMINI_API_KEY ? '***' + data.GEMINI_API_KEY.slice(-4) : 'Not set'}</p>
        `;

    } catch (error) {
        document.getElementById('configInfo').innerHTML = '<p>Failed to load configuration</p>';
    }
}

// Save settings
async function saveSettings(event) {
    event.preventDefault();

    const formData = {
        PINECONE_API_KEY: document.getElementById('pineconeKey').value,
        INDEX_NAME: document.getElementById('indexName').value,
        PINECONE_CLOUD: document.getElementById('pineconeCloud').value,
        PINECONE_REGION: document.getElementById('pineconeRegion').value,
        GEMINI_API_KEY: document.getElementById('geminiKey').value,
        GEMINI_MODEL: document.getElementById('geminiModel').value,
        CLIP_MODEL: document.getElementById('clipModel').value,
        REDUCE_DIM: document.getElementById('reduceDim').value
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save settings');
        }

        showStatus('Settings saved successfully! Please restart the server for changes to take effect.', 'success');
        loadConfigInfo();

    } catch (error) {
        showStatus('Failed to save settings: ' + error.message, 'error');
    }
}

// Test connection
async function testConnection() {
    showStatus('Testing API connections...', 'info');

    try {
        const response = await fetch('/api/validate');

        if (response.ok) {
            showStatus('All API connections are working correctly!', 'success');
        } else {
            const data = await response.json();
            let errorMsg = 'API connection test failed:\n\n';
            errorMsg += data.errors.join('\n');
            showStatus(errorMsg, 'error');
        }

    } catch (error) {
        showStatus('Connection test failed: ' + error.message, 'error');
    }
}

// Show status message
function showStatus(message, type) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.style.display = 'block';

    // Auto-hide after 10 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 10000);
    }
}
