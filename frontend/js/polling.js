/**
 * Real-time playlist sync polling manager
 * Polls playlist state every 3 seconds and updates UI on changes
 */

export class PollingManager {
    constructor(api, ui) {
        this.api = api;
        this.ui = ui;
        this.pollingIntervals = new Map(); // playlistId -> interval ID
        this.lastSnapshots = new Map(); // playlistId -> snapshot_id
        this.syncing = new Set(); // playlistIds currently syncing
        this.POLL_INTERVAL = 3000; // 3 seconds
    }

    /**
     * Start polling a playlist for real-time updates
     */
    startPolling(playlistId, onUpdate) {
        // Avoid duplicate polling
        if (this.pollingIntervals.has(playlistId)) {
            return;
        }
        
        // Poll immediately first time
        this.pollPlaylistState(playlistId, onUpdate);
        
        // Then set up interval
        const intervalId = setInterval(
            () => this.pollPlaylistState(playlistId, onUpdate),
            this.POLL_INTERVAL
        );
        
        this.pollingIntervals.set(playlistId, intervalId);
    }

    /**
     * Stop polling a playlist
     */
    stopPolling(playlistId) {
        const intervalId = this.pollingIntervals.get(playlistId);
        if (intervalId) {
            clearInterval(intervalId);
            this.pollingIntervals.delete(playlistId);
            this.lastSnapshots.delete(playlistId);
            this.syncing.delete(playlistId);
        }
    }

    /**
     * Stop all polling
     */
    stopAllPolling() {
        for (const playlistId of this.pollingIntervals.keys()) {
            this.stopPolling(playlistId);
        }
    }

    /**
     * Poll playlist state and check for changes
     */
    async pollPlaylistState(playlistId, onUpdate) {
        try {
            // Show syncing indicator
            this.syncing.add(playlistId);
            this.updateSyncIndicator(playlistId, true);

            const lastSnapshot = this.lastSnapshots.get(playlistId);
            
            const response = await this.api.get(
                `/playlists/${playlistId}/state?last_snapshot_id=${lastSnapshot || ''}`
            );

            // Store new snapshot
            if (response.snapshot_id) {
                this.lastSnapshots.set(playlistId, response.snapshot_id);
            }

            // If playlist state changed, update UI
            if (response.changed && response.playlist) {
                onUpdate(response.playlist);
            }

            // Hide syncing indicator
            this.syncing.delete(playlistId);
            this.updateSyncIndicator(playlistId, false);
        } catch (error) {
            this.syncing.delete(playlistId);
            this.updateSyncIndicator(playlistId, false);
            
            // Stop polling on 404 (playlist deleted)
            if (error.message.includes('404')) {
                this.stopPolling(playlistId);
                onUpdate(null); // Signal deletion
            }
        }
    }

    /**
     * Update sync indicator visibility
     */
    updateSyncIndicator(playlistId, visible) {
        const indicator = document.querySelector(
            `.sync-indicator[data-playlist-id="${playlistId}"]`
        );
        if (indicator) {
            indicator.style.opacity = visible ? '1' : '0.3';
        }
    }

    /**
     * Check if polling for a specific playlist
     */
    isPolling(playlistId) {
        return this.pollingIntervals.has(playlistId);
    }
}

export const createPollingManager = (api, ui) => {
    return new PollingManager(api, ui);
};
