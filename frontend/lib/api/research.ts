/* eslint-disable @typescript-eslint/no-explicit-any */
import { apiFetch, getAuthToken } from './client';

export interface StreamResearchOptions {
    query?: string;
    /** Omit (null) to start a new conversation — the backend creates the thread and returns its id in every event. */
    threadId: string | null;
    action?: 'approve' | 'reject' | 'edit';
    editedQuery?: string;
    onEvent: (event: any) => void;
    onError: (error: any) => void;
}

export async function streamResearch({
    query,
    threadId,
    action,
    editedQuery,
    onEvent,
    onError,
}: StreamResearchOptions) {
    try {
        // The backend only accepts the signed JWT, not Better Auth's opaque session id.
        const token = await getAuthToken();

        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

        // Route to /research/resume if an action is present, otherwise route to /research
        const endpoint = action ? '/research/resume' : '/research';

        // Construct body removing undefined parameters
        const bodyPayload: Record<string, any> = {};

        if (threadId !== null && threadId !== undefined) bodyPayload.thread_id = threadId;
        if (query !== undefined) bodyPayload.query = query;
        if (action !== undefined) bodyPayload.action = action;
        if (editedQuery !== undefined) bodyPayload.edited_query = editedQuery;

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            credentials: 'include',
            body: JSON.stringify(bodyPayload),
        });

        if (response.status === 401) {
            onError(new Error('HTTP 401: Unauthorized. Please sign in again.'));
            return;
        }

        if (!response.ok) {
            const errorText = await response.text().catch(() => '');
            onError(new Error(errorText || `Server returned status ${response.status}`));
            return;
        }

        if (!response.body) {
            onError(new Error('ReadableStream not supported by server response.'));
            return;
        }

        // Process SSE Stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');

            // Keep incomplete line in buffer
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith(':')) continue;

                if (trimmed.startsWith('data:')) {
                    const jsonStr = trimmed.slice(5).trim();
                    // The final line of the stream is the literal sentinel [DONE] (not JSON).
                    if (jsonStr === '[DONE]') continue;
                    if (!jsonStr) continue;
                    try {
                        const parsed = JSON.parse(jsonStr);
                        onEvent(parsed);
                    } catch (e) {
                        console.error('Failed to parse SSE line:', jsonStr, e);
                    }
                }
            }
        }
    } catch (err: any) {
        onError(err || new Error('Stream execution failed'));
    }
}

export async function fetchThreadHistory(threadId: string) {
    return apiFetch(`/sessions/${threadId}/messages`);
}