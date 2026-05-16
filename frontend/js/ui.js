export class UI {
    constructor() {
        this.playlistForm = document.getElementById('playlist-form');
        this.playlistNameInput = document.getElementById('playlist-name');
        this.playlistDescInput = document.getElementById('playlist-description');
        this.playlistsList = document.getElementById('playlists-list');
        this.statusDiv = document.getElementById('status');
        this.loadingDiv = document.getElementById('loading');
        this.healthStatus = document.getElementById('health-status');
    }

    showLoading(show = true) {
        if (show) {
            this.loadingDiv.classList.add('active');
        } else {
            this.loadingDiv.classList.remove('active');
        }
    }

    showError(message) {
        this.statusDiv.innerHTML = `<div class="error-message">❌ Error: ${message}</div>`;
        console.error(message);
    }

    showSuccess(message) {
        this.statusDiv.innerHTML = `<div class="success-message">✅ ${message}</div>`;
        setTimeout(() => {
            this.statusDiv.innerHTML = '';
        }, 3000);
    }

    updateHealthStatus(healthy, message = '') {
        if (healthy) {
            this.healthStatus.innerHTML = `<span class="status success">✓ Connected</span>`;
        } else {
            this.healthStatus.innerHTML = `<span class="status error">✗ Error: ${message}</span>`;
        }
    }

    clearForm() {
        this.playlistNameInput.value = '';
        this.playlistDescInput.value = '';
    }

    renderPlaylists(playlists) {
        if (!playlists || playlists.length === 0) {
            this.playlistsList.innerHTML = '<p style="color: var(--text-secondary);">No playlists yet. Create one to get started!</p>';
            return;
        }

        this.playlistsList.innerHTML = playlists.map(playlist => `
            <div class="playlist">
                <h3>${this.escapeHtml(playlist.name)}</h3>
                <p style="color: var(--text-secondary); font-size: 14px;">${this.escapeHtml(playlist.description || 'No description')}</p>
                <div class="playlist-meta">
                    <span>ID: ${playlist.id.substring(0, 8)}...</span>
                    <span style="margin-left: 15px;">Owner: ${playlist.owner_id.substring(0, 8)}...</span>
                </div>
            </div>
        `).join('');
    }

    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

export const ui = new UI();
