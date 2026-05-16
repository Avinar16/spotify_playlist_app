export class UI {
    constructor() {
        this.playlistForm = document.getElementById('playlist-form');
        this.playlistNameInput = document.getElementById('playlist-name');
        this.playlistDescInput = document.getElementById('playlist-description');
        this.playlistsList = document.getElementById('playlists-list');
        this.statusDiv = document.getElementById('status');
        this.loadingDiv = document.getElementById('loading');
        this.healthStatus = document.getElementById('health-status');
        
        // Auth elements
        this.authContainer = document.getElementById('auth-container');
        this.mainContainer = document.getElementById('main-container');
        this.userInfo = document.getElementById('user-info');
        this.logoutBtn = document.getElementById('logout-btn');
        this.loginTab = document.getElementById('login-tab');
        this.registerTab = document.getElementById('register-tab');
        this.loginForm = document.getElementById('login-form');
        this.registerForm = document.getElementById('register-form');
        this.loginEmail = document.getElementById('login-email');
        this.loginPassword = document.getElementById('login-password');
        this.registerEmail = document.getElementById('register-email');
        this.registerUsername = document.getElementById('register-username');
        this.registerPassword = document.getElementById('register-password');
        this.registerPasswordConfirm = document.getElementById('register-password-confirm');
        this.authStatus = document.getElementById('auth-status');
    }

    // Auth UI methods
    showAuthPage() {
        if (this.authContainer) this.authContainer.style.display = 'flex';
        if (this.mainContainer) this.mainContainer.style.display = 'none';
    }

    showMainPage() {
        if (this.authContainer) this.authContainer.style.display = 'none';
        if (this.mainContainer) this.mainContainer.style.display = 'block';
    }

    updateUserInfo(user) {
        if (this.userInfo && user) {
            this.userInfo.innerHTML = `👤 ${this.escapeHtml(user.username)}`;
        }
    }

    updateSpotifyStatus(user) {
        const spotifyStatus = document.getElementById('spotify-status');
        if (!spotifyStatus) return;

        if (user && user.spotify_id) {
            spotifyStatus.innerHTML = `<button id="spotify-connected-btn" class="btn-spotify connected">🎵 Connected</button>`;
        } else {
            spotifyStatus.innerHTML = `<button id="spotify-connect-btn" class="btn-spotify">🎵 Connect Spotify</button>`;
        }
    }

    switchToLoginTab() {
        if (this.loginTab && this.registerTab) {
            this.loginTab.classList.add('active');
            this.registerTab.classList.remove('active');
        }
        if (this.loginForm && this.registerForm) {
            this.loginForm.style.display = 'block';
            this.registerForm.style.display = 'none';
        }
    }

    switchToRegisterTab() {
        if (this.loginTab && this.registerTab) {
            this.loginTab.classList.remove('active');
            this.registerTab.classList.add('active');
        }
        if (this.loginForm && this.registerForm) {
            this.loginForm.style.display = 'none';
            this.registerForm.style.display = 'block';
        }
    }

    clearAuthForms() {
        if (this.loginEmail) this.loginEmail.value = '';
        if (this.loginPassword) this.loginPassword.value = '';
        if (this.registerEmail) this.registerEmail.value = '';
        if (this.registerUsername) this.registerUsername.value = '';
        if (this.registerPassword) this.registerPassword.value = '';
        if (this.registerPasswordConfirm) this.registerPasswordConfirm.value = '';
    }

    showLoading(show = true) {
        if (show) {
            this.loadingDiv.classList.add('active');
        } else {
            this.loadingDiv.classList.remove('active');
        }
    }

    showError(message) {
        const statusDiv = this.authStatus || this.statusDiv;
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="error-message">❌ Error: ${message}</div>`;
        }
        console.error(message);
    }

    showSuccess(message) {
        const statusDiv = this.authStatus || this.statusDiv;
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="success-message">✅ ${message}</div>`;
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 3000);
        }
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
            <div class="playlist-card" data-playlist-id="${playlist.id}">
                <div class="playlist-header">
                    <div class="playlist-info">
                        <h3 class="playlist-title">${this.escapeHtml(playlist.name)}</h3>
                        <p class="playlist-description">${this.escapeHtml(playlist.description || 'No description')}</p>
                    </div>
                    <div class="playlist-stats">
                        <span class="stat-badge">🎵 ${playlist.tracks ? playlist.tracks.length : 0}</span>
                        ${playlist.tracks && playlist.tracks.length > 0 ? `
                            <button class="btn-collapse" data-action="toggle-tracks" data-playlist-id="${playlist.id}" title="Toggle tracks">
                                <span class="collapse-icon">▼</span>
                            </button>
                        ` : ''}
                    </div>
                </div>

                ${playlist.tracks && playlist.tracks.length > 0 ? `
                    <div class="playlist-tracks-section" data-tracks-container="${playlist.id}">
                        <div class="tracks-header">
                            <span class="tracks-label">🎶 Tracks</span>
                            <span class="track-count">${playlist.tracks.length} items</span>
                        </div>
                        <div class="tracks-list">
                            ${playlist.tracks.map((track, index) => `
                                <div class="track-item">
                                    <span class="track-number">${index + 1}</span>
                                    ${track.track_image_url ? `
                                        <img class="track-image" src="${this.escapeHtml(track.track_image_url)}" alt="Album art" />
                                    ` : `
                                        <div class="track-image-placeholder">🎵</div>
                                    `}
                                    <div class="track-details">
                                        <span class="track-name" title="${this.escapeHtml(track.track_name || track.spotify_track_id)}">
                                            ${this.escapeHtml(track.track_name || track.spotify_track_id)}
                                        </span>
                                        ${track.track_artist ? `
                                            <span class="track-artist">${this.escapeHtml(track.track_artist)}</span>
                                        ` : ''}
                                    </div>
                                    <span class="track-time">${new Date(track.added_at).toLocaleDateString()}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : `
                    <div class="playlist-empty">
                        <p>📭 No tracks yet. Add some to get started!</p>
                    </div>
                `}
                
                <div class="playlist-actions">
                    <button class="btn-action btn-add" data-action="search-tracks" data-playlist-id="${playlist.id}">
                        <span>➕</span> Add Track
                    </button>
                    <button class="btn-action btn-invite" data-action="invite-collaborators" data-playlist-id="${playlist.id}">
                        <span>👥</span> Invite Friends
                    </button>
                    <button class="btn-action btn-save" data-action="save-spotify" data-playlist-id="${playlist.id}">
                        <span>💾</span> Save to Spotify
                    </button>
                </div>
            </div>
        `).join('');
        
        // Setup collapse/expand listeners
        this.setupCollapseListeners();
    }

    renderSearchResults(tracks) {
        if (!tracks || tracks.length === 0) {
            this.showError('No tracks found');
            return;
        }

        const html = tracks.map(track => `
            <div class="track-result">
                <div style="flex: 1;">
                    <p style="margin: 0; font-weight: 500;">${this.escapeHtml(track.name)}</p>
                    <p style="margin: 5px 0 0 0; color: var(--text-secondary); font-size: 14px;">${this.escapeHtml(track.artist)}</p>
                </div>
                <button class="btn-small" data-action="add-track" data-track-id="${track.id}">➕ Add</button>
            </div>
        `).join('');

        const searchModal = document.getElementById('search-modal');
        if (searchModal) {
            const resultsDiv = searchModal.querySelector('#search-results');
            if (resultsDiv) {
                resultsDiv.innerHTML = html;
            }
        }
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

    setupCollapseListeners() {
        document.querySelectorAll('.btn-collapse').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const playlistId = btn.dataset.playlistId;
                const tracksContainer = document.querySelector(`[data-tracks-container="${playlistId}"]`);
                
                if (tracksContainer) {
                    tracksContainer.classList.toggle('collapsed');
                    const icon = btn.querySelector('.collapse-icon');
                    if (icon) {
                        icon.textContent = tracksContainer.classList.contains('collapsed') ? '▶' : '▼';
                    }
                }
            });
        });
    }

    showInviteDialog(playlistId) {
        const modal = document.getElementById('invite-modal');
        if (!modal) {
            this.createInviteModal();
            return this.showInviteDialog(playlistId);
        }
        
        modal.style.display = 'flex';
        modal.dataset.playlistId = playlistId;
        
        const input = modal.querySelector('#invite-search-input');
        if (input) {
            input.focus();
            input.value = '';
        }
        
        // Load collaborators
        this.loadCollaborators(playlistId);
    }

    createInviteModal() {
        if (document.getElementById('invite-modal')) return;
        
        const modal = document.createElement('div');
        modal.id = 'invite-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Invite Collaborators</h2>
                    <button class="btn-close" data-action="close-invite-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="invite-form">
                        <input type="text" id="invite-search-input" placeholder="Search by username or email" />
                        <button id="btn-invite" class="btn-action">Invite</button>
                    </div>
                    <div id="collaborators-list" class="collaborators-list">
                        <p>Loading collaborators...</p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal handlers
        modal.querySelector('.modal-overlay').addEventListener('click', () => {
            this.closeInviteModal();
        });
        
        modal.querySelector('[data-action="close-invite-modal"]').addEventListener('click', () => {
            this.closeInviteModal();
        });
        
        // Invite button handler
        modal.querySelector('#btn-invite').addEventListener('click', () => {
            this.handleInviteClick();
        });
        
        // Enter key to invite
        modal.querySelector('#invite-search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleInviteClick();
            }
        });
    }

    closeInviteModal() {
        const modal = document.getElementById('invite-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async loadCollaborators(playlistId) {
        try {
            const { api } = await import('./api.js');
            const collaborators = await api.get(`/playlist/${playlistId}/collaborators`);
            const listDiv = document.getElementById('collaborators-list');
            
            if (!collaborators || collaborators.length === 0) {
                listDiv.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No collaborators yet</p>';
                return;
            }
            
            listDiv.innerHTML = `
                <div class="collaborators-header">🤝 Collaborators (${collaborators.length})</div>
                ${collaborators.map(collab => `
                    <div class="collaborator-item">
                        <div class="collaborator-info">
                            <span class="collaborator-name">${this.escapeHtml(collab.username)}</span>
                            <span class="collaborator-email">${this.escapeHtml(collab.email)}</span>
                        </div>
                        <button class="btn-remove-collab" data-action="remove-collaborator" data-user-id="${collab.id}" data-playlist-id="${playlistId}">✕</button>
                    </div>
                `).join('')}
            `;
        } catch (error) {
            console.error('Failed to load collaborators:', error);
            document.getElementById('collaborators-list').innerHTML = '<p style="color: red;">Failed to load collaborators</p>';
        }
    }

    async handleInviteClick() {
        const modal = document.getElementById('invite-modal');
        const playlistId = modal.dataset.playlistId;
        const input = modal.querySelector('#invite-search-input');
        const searchQuery = input.value.trim();
        
        if (!searchQuery) {
            this.showError('Please enter a username or email');
            return;
        }
        
        try {
            const { api } = await import('./api.js');
            const result = await api.post(`/playlist/${playlistId}/invite`, {
                search_query: searchQuery
            });
            
            this.showSuccess(`Added ${result.username} as collaborator!`);
            input.value = '';
            this.loadCollaborators(playlistId);
        } catch (error) {
            this.showError(error.message);
        }
    }
}

export const ui = new UI();
