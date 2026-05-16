import { api } from './api.js';
import { ui } from './ui.js';
import * as auth from './auth.js';

class App {
    constructor() {
        this.playlists = [];
        this.init();
    }

    async init() {
        console.log('🎵 Initializing Spotify Playlist Generator...');
        
        // Check authentication status
        const isAuthenticated = auth.isAuthenticated();
        
        if (isAuthenticated) {
            // User is logged in
            const user = auth.getCurrentUser();
            ui.updateUserInfo(user);
            ui.updateSpotifyStatus(user);
            ui.showMainPage();
            
            // Set up main app
            this.setupEventListeners();
            this.setupSpotifyListeners();
            await this.checkHealth();
            await this.loadPlaylists();
            
            // Listen for Spotify OAuth callback
            this.setupSpotifyCallback();
        } else {
            // User is not logged in
            ui.showAuthPage();
            this.setupAuthEventListeners();
        }
    }

    setupEventListeners() {
        ui.playlistForm.addEventListener('submit', (e) => this.handleCreatePlaylist(e));
        if (ui.logoutBtn) {
            ui.logoutBtn.addEventListener('click', () => this.handleLogout());
        }
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSearchModal();
            }
        });
        
        // Event delegation for playlist actions
        document.addEventListener('click', async (e) => {
            if (e.target.dataset.action === 'search-tracks') {
                await this.openSearchModal(e.target.dataset.playlistId);
            }
            if (e.target.dataset.action === 'invite-collaborators') {
                ui.showInviteDialog(e.target.dataset.playlistId);
            }
            if (e.target.dataset.action === 'save-spotify') {
                await this.savePlaylistToSpotify(e.target.dataset.playlistId);
            }
            if (e.target.dataset.action === 'add-track') {
                await this.addTrackToPlaylist(e.target.dataset.trackId);
            }
            if (e.target.dataset.action === 'remove-collaborator') {
                await this.removeCollaborator(e.target.dataset.playlistId, e.target.dataset.userId);
            }
            if (e.target.dataset.action === 'close-invite-modal') {
                ui.closeInviteModal();
            }
        });
        
        // Search modal close button
        const closeBtn = document.getElementById('close-search-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeSearchModal();
            });
        }
        
        // Close modal on overlay click
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('search-modal');
            if (modal && modal.style.display === 'flex' && e.target === modal.querySelector('.modal-overlay')) {
                this.closeSearchModal();
            }
        });
        
        // Search input - live search
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                if (e.target.value.length >= 2) {
                    searchTimeout = setTimeout(() => {
                        this.performSearch(e.target.value);
                    }, 500);
                }
            });
        }
    }

    setupAuthEventListeners() {
        // Tab switching
        if (ui.loginTab) {
            ui.loginTab.addEventListener('click', () => ui.switchToLoginTab());
        }
        if (ui.registerTab) {
            ui.registerTab.addEventListener('click', () => ui.switchToRegisterTab());
        }

        // Login form
        if (ui.loginForm) {
            ui.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Register form
        if (ui.registerForm) {
            ui.registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        
        const email = ui.loginEmail?.value?.trim();
        const password = ui.loginPassword?.value?.trim();

        if (!email || !password) {
            ui.showError('Email and password are required');
            return;
        }

        ui.showLoading(true);
        try {
            const result = await auth.login(email, password);
            
            if (result.success) {
                ui.showSuccess('Login successful! 🎉');
                ui.clearAuthForms();
                // Reload the app
                setTimeout(() => location.reload(), 1000);
            } else {
                ui.showError(result.error || 'Login failed');
            }
        } catch (error) {
            ui.showError(error.message);
        } finally {
            ui.showLoading(false);
        }
    }

    async handleRegister(event) {
        event.preventDefault();
        
        const email = ui.registerEmail?.value?.trim();
        const username = ui.registerUsername?.value?.trim();
        const password = ui.registerPassword?.value?.trim();
        const passwordConfirm = ui.registerPasswordConfirm?.value?.trim();

        if (!email || !username || !password || !passwordConfirm) {
            ui.showError('All fields are required');
            return;
        }

        if (password !== passwordConfirm) {
            ui.showError('Passwords do not match');
            return;
        }

        ui.showLoading(true);
        try {
            const result = await auth.register(email, username, password);
            
            if (result.success) {
                ui.showSuccess('Registration successful! 🎉');
                ui.clearAuthForms();
                // Reload the app
                setTimeout(() => location.reload(), 1000);
            } else {
                ui.showError(result.error || 'Registration failed');
            }
        } catch (error) {
            ui.showError(error.message);
        } finally {
            ui.showLoading(false);
        }
    }

    handleLogout() {
        if (confirm('Are you sure you want to logout?')) {
            auth.logout();
            location.reload();
        }
    }

    setupSpotifyListeners() {
        // Listen for Spotify connect button
        document.addEventListener('click', async (e) => {
            if (e.target?.id === 'spotify-connect-btn') {
                e.preventDefault();
                await this.handleSpotifyConnect();
            }
            if (e.target?.id === 'spotify-connected-btn') {
                e.preventDefault();
                await this.handleSpotifyUnlink();
            }
        });
        
        // Listen for Spotify token expiry
        window.addEventListener('spotify-token-expired', () => {
            ui.showError('🎵 Spotify session expired. Please reconnect your account.');
            this.handleSpotifyConnect();
        });
    }

    setupSpotifyCallback() {
        // Listen for messages from Spotify callback popup
        window.addEventListener('message', async (e) => {
            if (e.data.type === 'SPOTIFY_AUTH_CODE') {
                const code = e.data.code;
                const codeVerifier = sessionStorage.getItem('spotify_code_verifier');
                
                if (code && codeVerifier) {
                    await this.handleSpotifyCallback(code, codeVerifier);
                }
            } else if (e.data.type === 'SPOTIFY_AUTH_ERROR') {
                ui.showError(`Spotify auth error: ${e.data.error}`);
            }
        });
    }

    async handleSpotifyConnect() {
        try {
            const spotify = await import('./spotify.js');
            ui.showLoading(true);
            const result = await spotify.openSpotifyAuth();
            
            if (!result.success) {
                ui.showError(result.error || 'Failed to open Spotify auth');
            }
        } catch (error) {
            ui.showError(`Error: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }

    async handleSpotifyCallback(code, codeVerifier) {
        try {
            const spotify = await import('./spotify.js');
            ui.showLoading(true);
            
            const result = await spotify.linkSpotifyAccount(code, codeVerifier);
            
            if (result.success) {
                ui.showSuccess('Spotify account linked successfully! 🎵');
                // Update UI and refresh user info
                const user = auth.getCurrentUser();
                const updatedUser = await (await import('./api.js')).api.getCurrentUser();
                auth.setCurrentUser(updatedUser);
                ui.updateUserInfo(updatedUser);
                ui.updateSpotifyStatus(updatedUser);
                
                // Clear stored verifier
                sessionStorage.removeItem('spotify_code_verifier');
            } else {
                ui.showError(result.error || 'Failed to link Spotify account');
            }
        } catch (error) {
            ui.showError(`Spotify linking error: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }

    async handleSpotifyUnlink() {
        if (!confirm('Are you sure you want to unlink your Spotify account?')) {
            return;
        }

        try {
            const spotify = await import('./spotify.js');
            ui.showLoading(true);
            
            const result = await spotify.unlinkSpotifyAccount();
            
            if (result.success) {
                ui.showSuccess('Spotify account unlinked');
                // Update UI
                const user = auth.getCurrentUser();
                user.spotify_id = null;
                auth.setCurrentUser(user);
                ui.updateUserInfo(user);
                ui.updateSpotifyStatus(user);
            } else {
                ui.showError(result.error || 'Failed to unlink Spotify account');
            }
        } catch (error) {
            ui.showError(`Error: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }

    async checkHealth() {
        ui.showLoading(true);
        try {
            const health = await api.healthCheck();
            ui.updateHealthStatus(true);
            console.log('✅ Backend is healthy:', health);
        } catch (error) {
            ui.updateHealthStatus(false, error.message);
            console.error('❌ Health check failed:', error);
        } finally {
            ui.showLoading(false);
        }
    }

    async loadPlaylists() {
        ui.showLoading(true);
        try {
            this.playlists = await api.getPlaylists();
            
            // Load tracks for each playlist
            for (let playlist of this.playlists) {
                try {
                    playlist.tracks = await api.getPlaylistTracks(playlist.id);
                } catch (error) {
                    console.warn(`Failed to load tracks for playlist ${playlist.id}:`, error);
                    playlist.tracks = [];
                }
            }
            
            ui.renderPlaylists(this.playlists);
            console.log(`✅ Loaded ${this.playlists.length} playlists`);
        } catch (error) {
            ui.showError(error.message);
            console.error('Error loading playlists:', error);
        } finally {
            ui.showLoading(false);
        }
    }

    async handleCreatePlaylist(event) {
        event.preventDefault();
        
        const name = ui.playlistNameInput.value.trim();
        const description = ui.playlistDescInput.value.trim();

        if (!name) {
            ui.showError('Playlist name is required');
            return;
        }

        ui.showLoading(true);
        try {
            const newPlaylist = await api.createPlaylist(name, description);
            this.playlists.push(newPlaylist);
            ui.renderPlaylists(this.playlists);
            ui.clearForm();
            ui.showSuccess('Playlist created successfully! 🎉');
            console.log('✅ Playlist created:', newPlaylist);
        } catch (error) {
            ui.showError(error.message);
            console.error('Error creating playlist:', error);
        } finally {
            ui.showLoading(false);
        }
    }

    async openSearchModal(playlistId) {
        this.currentPlaylistId = playlistId;
        const modal = document.getElementById('search-modal');
        if (modal) {
            modal.style.display = 'flex';
            const input = document.getElementById('search-input');
            if (input) input.focus();
        }
    }

    closeSearchModal() {
        const modal = document.getElementById('search-modal');
        if (modal) {
            modal.style.display = 'none';
            this.currentPlaylistId = null;
        }
    }

    async performSearch(query) {
        try {
            ui.showLoading(true);
            const tracks = await api.searchTracks(query, 10);
            ui.renderSearchResults(tracks);
        } catch (error) {
            ui.showError(`Search failed: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }

    async addTrackToPlaylist(trackId) {
        if (!this.currentPlaylistId) {
            ui.showError('No playlist selected');
            return;
        }

        try {
            ui.showLoading(true);
            await api.addTrackToPlaylist(this.currentPlaylistId, trackId);
            ui.showSuccess('Track added to playlist! ✅');
            
            // Refresh playlists but keep modal open
            await this.loadPlaylists();
            
            // Clear search to show fresh state
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.value = '';
                const resultsDiv = document.getElementById('search-results');
                if (resultsDiv) {
                    resultsDiv.innerHTML = '<p style="color: var(--text-secondary);">Type to search...</p>';
                }
            }
        } catch (error) {
            ui.showError(`Failed to add track: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }

    async savePlaylistToSpotify(playlistId) {
        const playlist = this.playlists.find(p => p.id === playlistId);
        if (!playlist) {
            ui.showError('Playlist not found');
            return;
        }

        try {
            ui.showLoading(true);
            
            // First create the playlist on Spotify
            const result = await api.createPlaylistOnSpotify(
                playlistId,
                playlist.name,
                playlist.description
            );
            
            console.log('✅ Playlist created on Spotify:', result);
            
            // Then sync all tracks
            const syncResult = await api.syncTracksToSpotify(playlistId);
            console.log('✅ Tracks synced:', syncResult);
            
            ui.showSuccess(`Playlist saved to Spotify! 🎵 (${syncResult.synced_count} tracks)`);
            await this.loadPlaylists();
        } catch (error) {
            ui.showError(`Failed to save playlist: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }

    async removeCollaborator(playlistId, userId) {
        if (!confirm('Remove this collaborator?')) {
            return;
        }

        try {
            ui.showLoading(true);
            await api.delete(`/playlist/${playlistId}/collaborators/${userId}`);
            ui.showSuccess('Collaborator removed');
            ui.loadCollaborators(playlistId);
        } catch (error) {
            ui.showError(`Failed to remove collaborator: ${error.message}`);
        } finally {
            ui.showLoading(false);
        }
    }
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
