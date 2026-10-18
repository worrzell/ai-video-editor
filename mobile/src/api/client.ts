import * as SecureStore from 'expo-secure-store';

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export { BASE_URL };

export const TOKEN_KEY = 'access_token';

export const getToken = (): Promise<string | null> =>
  SecureStore.getItemAsync(TOKEN_KEY);

export const setToken = (token: string): Promise<void> =>
  SecureStore.setItemAsync(TOKEN_KEY, token);

export const clearToken = (): Promise<void> =>
  SecureStore.deleteItemAsync(TOKEN_KEY);

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    throw new Error('AUTH_REQUIRED');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? 'Request failed');
  }

  const contentType = res.headers.get('content-type') ?? '';
  return contentType.includes('application/json')
    ? res.json()
    : (res.text() as unknown as T);
}
