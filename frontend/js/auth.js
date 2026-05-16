/**
 * Authentication module - handles login, registration, and token management
 */

const AUTH_KEY = 'spotify_playlist_auth';
const API_BASE = '/api';

/**
 * Get stored authentication data
 */
export function getAuthData() {
    const stored = localStorage.getItem(AUTH_KEY);
    return stored ? JSON.parse(stored) : null;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
    const auth = getAuthData();
    return auth && auth.access_token ? true : false;
}

/**
 * Get current user
 */
export function getCurrentUser() {
    const auth = getAuthData();
    return auth ? auth.user : null;
}

/**
 * Get access token
 */
export function getAccessToken() {
    const auth = getAuthData();
    return auth ? auth.access_token : null;
}

/**
 * Set current user in storage
 */
export function setCurrentUser(user) {
    const auth = getAuthData();
    if (auth) {
        auth.user = user;
        setAuthData(auth);
    }
}

/**
 */
export function getAuthHeader() {
    const token = getAccessToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

/**
 * Store authentication data
 */
function setAuthData(data) {
    localStorage.setItem(AUTH_KEY, JSON.stringify(data));
}

/**
 * Clear authentication data (logout)
 */
export function clearAuthData() {
    localStorage.removeItem(AUTH_KEY);
}

/**
 * Register new user
 */
export async function register(email, username, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                username,
                password,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Registration failed');
        }

        // Store auth data
        setAuthData({
            user: data.user,
            access_token: data.access_token,
            refresh_token: data.refresh_token,
        });

        return {
            success: true,
            user: data.user,
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}

/**
 * Login user
 */
export async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        // Store auth data
        setAuthData({
            user: data.user,
            access_token: data.access_token,
            refresh_token: data.refresh_token,
        });

        return {
            success: true,
            user: data.user,
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}

/**
 * Logout user
 */
export function logout() {
    clearAuthData();
    return { success: true };
}

/**
 * Refresh access token
 */
export async function refreshAccessToken() {
    const auth = getAuthData();
    if (!auth || !auth.refresh_token) {
        return { success: false, error: 'No refresh token' };
    }

    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                refresh_token: auth.refresh_token,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Token refresh failed');
        }

        // Update access token
        auth.access_token = data.access_token;
        setAuthData(auth);

        return {
            success: true,
            access_token: data.access_token,
        };
    } catch (error) {
        // Clear auth on refresh failure
        clearAuthData();
        return {
            success: false,
            error: error.message,
        };
    }
}

/**
 * Get current user from server
 */
export async function fetchCurrentUser() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: getAuthHeader(),
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                clearAuthData();
            }
            throw new Error(data.detail || 'Failed to fetch user');
        }

        return {
            success: true,
            user: data,
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
        };
    }
}
