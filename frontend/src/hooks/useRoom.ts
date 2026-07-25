import { useState, useEffect, useCallback, useRef } from 'react';
import { roomApi } from '@/services/api';
import type { Room } from '@/types';

function roomsEqual(a: Room[], b: Room[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    const ra = a[i];
    const rb = b[i];
    if (
      ra.room_id !== rb.room_id ||
      ra.room_name !== rb.room_name ||
      ra.anchor_name !== rb.anchor_name ||
      ra.status !== rb.status ||
      ra.error_msg !== rb.error_msg
    ) {
      return false;
    }
  }
  return true;
}

export function useRoom() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const prevRoomsRef = useRef<Room[]>([]);

  const fetchRooms = useCallback(async (isPolling = false) => {
    try {
      if (!isPolling) {
        setLoading(true);
        setError(null);
      }
      const response = await roomApi.getAll();
      if (response.code === 0) {
        const newRooms = response.data || [];
        if (!roomsEqual(prevRoomsRef.current, newRooms)) {
          setRooms(newRooms);
          prevRoomsRef.current = newRooms;
        }
      } else {
        if (!isPolling) {
          setError(response.msg);
        }
      }
    } catch (e) {
      if (!isPolling) {
        setError('获取房间列表失败');
        console.error('Fetch rooms failed:', e);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const addRoom = useCallback(async (roomId: number) => {
    try {
      const response = await roomApi.add(roomId);
      if (response.code === 0) {
        await fetchRooms();
      }
      return response;
    } catch (e) {
      console.error('Add room failed:', e);
      throw e;
    }
  }, [fetchRooms]);

  const deleteRoom = useCallback(async (roomId: number) => {
    try {
      const response = await roomApi.delete(roomId);
      if (response.code === 0) {
        await fetchRooms();
        return true;
      } else {
        throw new Error(response.msg);
      }
    } catch (e) {
      console.error('Delete room failed:', e);
      throw e;
    }
  }, [fetchRooms]);

  const startMonitor = useCallback(async (roomId: number) => {
    try {
      const response = await roomApi.startMonitor(roomId);
      if (response.code === 0) {
        await fetchRooms();
      }
      return response;
    } catch (e) {
      console.error('Start monitor failed:', e);
      throw e;
    }
  }, [fetchRooms]);

  const stopMonitor = useCallback(async (roomId: number) => {
    try {
      const response = await roomApi.stopMonitor(roomId);
      if (response.code === 0) {
        await fetchRooms();
      }
      return response;
    } catch (e) {
      console.error('Stop monitor failed:', e);
      throw e;
    }
  }, [fetchRooms]);

  useEffect(() => {
    fetchRooms();
    const interval = setInterval(() => {
      if (!document.hidden) {
        fetchRooms(true);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchRooms]);

  return { rooms, loading, error, addRoom, deleteRoom, startMonitor, stopMonitor };
}
