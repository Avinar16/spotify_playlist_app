const API_BASE = '/api';

export class APIClient {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `API Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // Playlists
    async getPlaylists() {
        return this.get('/playlists');
    }

    async createPlaylist(name, description = '') {
        return this.post('/playlists', { name, description });
    }

    async getPlaylist(playlistId) {
        return this.get(`/playlists/${playlistId}`);
    }

    // Health check
    async healthCheck() {
        return this.get('/health');
    }

    // Test endpoint
    async testData() {
        return this.get('/test-data');
    }
}

export const api = new APIClient();
