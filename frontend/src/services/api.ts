import type { Room, DanmuStats, ApiResponse, DanmuListResponse, DanmuSession, DanmuRecord } from '@/types';

const BASE_URL = '/api';
const DEFAULT_TIMEOUT = 10000;

interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE';
  params?: Record<string, any>;
  body?: any;
  timeout?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    params,
    body,
    timeout = DEFAULT_TIMEOUT,
  } = options;

  let url = `${BASE_URL}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('请求超时');
    }
    console.error('API Error:', error);
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const roomApi = {
  getAll: async () => {
    return request<ApiResponse<Room[]>>('/rooms');
  },
  getById: async (roomId: number) => {
    return request<ApiResponse<Room>>(`/rooms/${roomId}/info`);
  },
  add: async (roomId: number) => {
    return request<ApiResponse<Room>>('/rooms', { method: 'POST', body: { roomId } });
  },
  delete: async (roomId: number) => {
    return request<ApiResponse>(`/rooms/${roomId}`, { method: 'DELETE' });
  },
  startMonitor: async (roomId: number) => {
    return request<ApiResponse>(`/rooms/${roomId}/monitor`, { method: 'POST' });
  },
  stopMonitor: async (roomId: number) => {
    return request<ApiResponse>(`/rooms/${roomId}/monitor/stop`, { method: 'POST' });
  },
};

export const danmuApi = {
  getList: async (roomId: number, params?: { page?: number; pageSize?: number }) => {
    return request<ApiResponse<DanmuListResponse>>(`/danmu/${roomId}`, { params });
  },
  getStats: async (roomId: number) => {
    return request<ApiResponse<DanmuStats>>(`/danmu/${roomId}/stats`);
  },
};

export const sessionApi = {
  getList: async (roomId: number) => {
    return request<ApiResponse<DanmuSession[]>>(`/sessions/${roomId}`);
  },
  getDetail: async (roomId: number, sessionId: number) => {
    return request<ApiResponse<{ session: DanmuSession; danmuList: DanmuRecord[] }>>(
      `/sessions/${roomId}/${sessionId}`
    );
  },
  delete: async (roomId: number, sessionId: number) => {
    return request<ApiResponse>(`/sessions/${roomId}/${sessionId}`, { method: 'DELETE' });
  },
};
