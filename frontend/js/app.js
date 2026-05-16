import { api } from './api.js';
import { ui } from './ui.js';

class App {
    constructor() {
        this.playlists = [];
        this.init();
    }

    async init() {
        console.log('🎵 Initializing Spotify Playlist Generator...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Check health
        await this.checkHealth();
        
        // Load playlists
        await this.loadPlaylists();
    }

    setupEventListeners() {
        ui.playlistForm.addEventListener('submit', (e) => this.handleCreatePlaylist(e));
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
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
