import { useState, useCallback, useEffect, useRef } from 'react';
import type { DanmuRecord } from '@/types';
import { useWebSocket } from '@/context/WebSocketContext';

const MAX_DANMAKU = 1000;
const THROTTLE_MS = 100;

interface UseDanmakuOptions {
  roomId: number | null;
  isMonitoring?: boolean;
}

export function useDanmaku({ roomId, isMonitoring = false }: UseDanmakuOptions) {
  const [danmakuList, setDanmakuList] = useState<DanmuRecord[]>([]);
  const [historyCount, setHistoryCount] = useState(0);
  const { subscribe, unsubscribe, status: wsStatus } = useWebSocket();
  const pendingDanmaku = useRef<DanmuRecord[]>([]);
  const throttleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMonitoringRef = useRef(isMonitoring);

  isMonitoringRef.current = isMonitoring;

  const handleDanmu = useCallback((record: DanmuRecord) => {
    console.log('handleDanmu called:', record.room_id, record.username, record.content);
    pendingDanmaku.current.push(record);

    if (!throttleTimer.current) {
      throttleTimer.current = setTimeout(() => {
        setDanmakuList((prev) => {
          const updated = [...prev, ...pendingDanmaku.current];
          pendingDanmaku.current = [];
          throttleTimer.current = null;
          return updated.slice(-MAX_DANMAKU);
        });
      }, THROTTLE_MS);
    }
  }, []);

  const setInitialData = useCallback((data: DanmuRecord[]) => {
    const sliced = data.slice(-MAX_DANMAKU);
    setHistoryCount(sliced.length);
    setDanmakuList(sliced);
  }, []);

  const clearAndStartNewSession = useCallback(() => {
    setDanmakuList([]);
    setHistoryCount(0);
  }, []);

  const markAsHistory = useCallback(() => {
    setDanmakuList((prev) => {
      setHistoryCount(prev.length);
      return prev;
    });
  }, []);

  useEffect(() => {
    console.log('useDanmaku effect:', { roomId, isMonitoring });

    if (!roomId) {
      return;
    }

    if (isMonitoring) {
      console.log('Subscribing to room:', roomId);
      subscribe(roomId, handleDanmu);
    }

    return () => {
      if (throttleTimer.current) {
        clearTimeout(throttleTimer.current);
        throttleTimer.current = null;
      }
      if (roomId && isMonitoringRef.current) {
        console.log('Cleanup: unsubscribing from:', roomId);
        unsubscribe(roomId, handleDanmu);
      }
    };
  }, [roomId, isMonitoring, subscribe, unsubscribe, handleDanmu]);

  return { danmakuList, historyCount, setInitialData, clearAndStartNewSession, markAsHistory, wsStatus };
}
