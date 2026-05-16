const API_BASE = '/api';

export class APIClient {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        
        // Import auth module dynamically to avoid circular imports
        const { getAuthHeader } = await import('./auth.js');
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader(),
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                const error = await response.json().catch(() => ({}));
                const errorDetail = error.detail || '';
                
                // Check if it's a Spotify token expiry issue
                if (errorDetail.includes('expired') || errorDetail.includes('Spotify session')) {
                    // Emit event to trigger Spotify re-authorization
                    window.dispatchEvent(new CustomEvent('spotify-token-expired', {
                        detail: { message: errorDetail }
                    }));
                    throw new Error(errorDetail || 'Spotify session expired. Please reconnect.');
                }
                
                // Otherwise, user auth expired
                const { logout } = await import('./auth.js');
                logout();
                window.location.hash = '#login';
                throw new Error('Session expired. Please login again.');
            }
            
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

    async getPlaylistTracks(playlistId) {
        return this.get(`/playlists/${playlistId}/tracks`);
    }

    // Playlist management
    async searchTracks(query, limit = 20) {
        return this.post('/playlist/search-tracks', { query, limit });
    }

    async addTrackToPlaylist(playlistId, spotifyTrackId) {
        return this.post(`/playlist/${playlistId}/add-track`, { spotify_track_id: spotifyTrackId });
    }

    async createPlaylistOnSpotify(playlistId, name, description = '') {
        return this.post(`/playlist/${playlistId}/create-on-spotify`, { name, description });
    }

    async syncTracksToSpotify(playlistId) {
        return this.post(`/playlist/${playlistId}/sync-tracks`, {});
    }

    // Health check
    async healthCheck() {
        return this.get('/health');
    }

    // Get current user
    async getCurrentUser() {
        return this.get('/auth/me');
    }

    // Test endpoint
    async testData() {
        return this.get('/test-data');
    }
}

export const api = new APIClient();
