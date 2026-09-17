/* eslint-disable @typescript-eslint/no-explicit-any */
import { authClient } from '@/lib/auth/client';

// Sanitize base URL by stripping any trailing slash
const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_BASE_URL = RAW_API_URL.replace(/\/$/, '');

export async function apiFetch<T = any>(
    endpoint: string, 
    options: RequestInit = {}
): Promise<T> {
    // Ensure endpoint always begins with a single leading slash
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const targetUrl = `${API_BASE_URL}${cleanEndpoint}`;

    // 1. Retrieve the active session token dynamically
    const session = await authClient.getSession();
    const token = session?.data?.session?.token;

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // 2. Execute the request
    let response: Response;
    try {
        response = await fetch(targetUrl, {
            ...options,
            headers,
        });
    } catch (networkError) {
        console.error(`[apiFetch] Socket/Network failure reaching: ${targetUrl}`, networkError);
        throw new Error(
            `Failed to connect to backend at ${targetUrl}. Check CORS policy or server availability.`
        );
    }

    if (response.status === 401) {
        throw new Error('401: Unauthorized access. Token may be expired.');
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `API Request failed with status ${response.status}`);
    }

    return response.json();
}