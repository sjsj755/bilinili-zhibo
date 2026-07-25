import axios from 'axios';
import type { Room, DanmuStats, ApiResponse, DanmuListResponse, DanmuSession, DanmuRecord } from '@/types';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const roomApi = {
  getAll: async () => {
    const result = await api.get('/rooms');
    return result as unknown as ApiResponse<Room[]>;
  },
  getById: async (roomId: number) => {
    const result = await api.get(`/rooms/${roomId}/info`);
    return result as unknown as ApiResponse<Room>;
  },
  add: async (roomId: number) => {
    const result = await api.post('/rooms', { roomId });
    return result as unknown as ApiResponse<Room>;
  },
  delete: async (roomId: number) => {
    const result = await api.delete(`/rooms/${roomId}`);
    return result as unknown as ApiResponse;
  },
  startMonitor: async (roomId: number) => {
    const result = await api.post(`/rooms/${roomId}/monitor`);
    return result as unknown as ApiResponse;
  },
  stopMonitor: async (roomId: number) => {
    const result = await api.post(`/rooms/${roomId}/monitor/stop`);
    return result as unknown as ApiResponse;
  },
};

export const danmuApi = {
  getList: async (roomId: number, params?: { page?: number; pageSize?: number }) => {
    const result = await api.get(`/danmu/${roomId}`, { params });
    return result as unknown as ApiResponse<DanmuListResponse>;
  },
  getStats: async (roomId: number) => {
    const result = await api.get(`/danmu/${roomId}/stats`);
    return result as unknown as ApiResponse<DanmuStats>;
  },
};

export const sessionApi = {
  getList: async (roomId: number) => {
    const result = await api.get(`/sessions/${roomId}`);
    return result as unknown as ApiResponse<DanmuSession[]>;
  },
  getDetail: async (roomId: number, sessionId: number) => {
    const result = await api.get(`/sessions/${roomId}/${sessionId}`);
    return result as unknown as ApiResponse<{ session: DanmuSession; danmuList: DanmuRecord[] }>;
  },
  delete: async (roomId: number, sessionId: number) => {
    const result = await api.delete(`/sessions/${roomId}/${sessionId}`);
    return result as unknown as ApiResponse;
  },
};

export default api;
