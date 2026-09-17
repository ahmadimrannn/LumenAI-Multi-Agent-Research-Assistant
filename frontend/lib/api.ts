import { apiFetch } from './api/client';

export interface RemoteSession {
    thread_id: string;
    title?: string;
    created_at?: string;
    updated_at?: string;
}

export async function fetchUserSessions(): Promise<{ sessions: RemoteSession[] }> {
    try {
        return await apiFetch<{ sessions: RemoteSession[] }>('/sessions');
    } catch (error) {
        console.error('Failed to fetch user sessions:', error);
        return { sessions: [] };
    }
}