/**
 * Spotify authentication and linking module
 */

const API_BASE = '/api';

/**
 * Get Spotify authorization URL
 */
export async function getSpotifyAuthUrl() {
    try {
        const { getAuthHeader } = await import('./auth.js');
        const response = await fetch(`${API_BASE}/spotify/auth-url`, {
            headers: getAuthHeader(),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get auth URL');
        }

        return await response.json();
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}

/**
 * Link Spotify account
 */
export async function linkSpotifyAccount(code, codeVerifier) {
    try {
        const { getAuthHeader } = await import('./auth.js');
        const response = await fetch(`${API_BASE}/spotify/link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader(),
            },
            body: JSON.stringify({
                code,
                code_verifier: codeVerifier,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to link Spotify account');
        }

        return {
            success: true,
            data: data,
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}

/**
 * Unlink Spotify account
 */
export async function unlinkSpotifyAccount() {
    try {
        const { getAuthHeader } = await import('./auth.js');
        const response = await fetch(`${API_BASE}/spotify/unlink`, {
            method: 'POST',
            headers: getAuthHeader(),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to unlink Spotify account');
        }

        return {
            success: true,
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}

/**
 * Open Spotify authorization popup
 */
export async function openSpotifyAuth() {
    try {
        // Get auth URL and code verifier
        const urlData = await getSpotifyAuthUrl();
        if (!urlData.auth_url) {
            throw new Error(urlData.error || 'Failed to get auth URL');
        }

        // Store code verifier in session storage (will be lost on page reload but that's ok)
        sessionStorage.setItem('spotify_code_verifier', urlData.code_verifier);

        // Open popup
        const width = 400;
        const height = 600;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;

        const popup = window.open(
            urlData.auth_url,
            'Spotify Auth',
            `width=${width},height=${height},left=${left},top=${top}`
        );

        if (!popup) {
            throw new Error('Failed to open Spotify auth window');
        }

        return { success: true, popup };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}
