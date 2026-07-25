import React, { createContext, useContext, useCallback, useEffect, useState, useRef } from 'react';
import type { DanmuRecord, WsSubscribeMessage, RealtimeStats } from '@/types';

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketContextType {
  subscribe: (roomId: number, onDanmu: (record: DanmuRecord) => void) => void;
  unsubscribe: (roomId: number, onDanmu?: (record: DanmuRecord) => void) => void;
  subscribeStats: (roomId: number, onStats: (stats: RealtimeStats) => void) => void;
  unsubscribeStats: (roomId: number, onStats?: (stats: RealtimeStats) => void) => void;
  status: WsStatus;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<WsStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const subscribedRoomsRef = useRef<Set<number>>(new Set());
  const danmuHandlersRef = useRef<Map<number, Set<(record: DanmuRecord) => void>>>(new Map());
  const statsHandlersRef = useRef<Map<number, Set<(stats: RealtimeStats) => void>>>(new Map());
  const isConnectingRef = useRef(false);
  const statusRef = useRef(status);

  statusRef.current = status;

  const getWsUrl = () => {
    if (import.meta.env.DEV) {
      return '/ws';
    }
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:3001';
    const wsProtocol = backendUrl.startsWith('https') ? 'wss:' : 'ws:';
    const host = backendUrl.replace(/^https?:\/\//, '');
    return `${wsProtocol}//${host}/ws`;
  };

  const connect = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] 已连接，跳过重复连接');
      return;
    }
    if (isConnectingRef.current) {
      console.log('[WebSocket] 正在连接中，跳过重复连接');
      return;
    }

    if (ws) {
      try {
        ws.close(1000);
      } catch {
        // ignore
      }
    }

    isConnectingRef.current = true;
    setStatus('connecting');
    const wsUrl = getWsUrl();
    console.log('[WebSocket] 开始连接:', wsUrl);

    const newWs = new WebSocket(wsUrl);

    newWs.onopen = () => {
      isConnectingRef.current = false;
      setStatus('connected');
      reconnectAttemptRef.current = 0;
      console.log('[WebSocket] 连接成功');

      for (const roomId of subscribedRoomsRef.current) {
        try {
          newWs.send(JSON.stringify({ type: 'subscribe', roomId } as WsSubscribeMessage));
          console.log('[WebSocket] 重订阅房间:', roomId);
        } catch {
          console.warn(`[WebSocket] Failed to resubscribe room ${roomId}`);
        }
      }
    };

    newWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.log('[WebSocket] 收到消息:', msg.type, msg.data?.room_id);
        if (msg.type === 'danmu' && msg.data) {
          const roomId = msg.data.room_id;
          const handlers = danmuHandlersRef.current.get(roomId);
          if (handlers) {
            console.log('[WebSocket] 处理弹幕，房间:', roomId, '处理器数量:', handlers.size);
            for (const handler of handlers) {
              handler(msg.data);
            }
          } else {
            console.warn('[WebSocket] 没有找到房间', roomId, '的处理器');
          }
        } else if (msg.type === 'realtime_stats' && msg.data) {
          const statsData = Array.isArray(msg.data) ? msg.data : [msg.data];
          for (const stats of statsData) {
            const roomId = stats.room_id;
            const handlers = statsHandlersRef.current.get(roomId);
            if (handlers) {
              console.log('[WebSocket] 处理实时统计，房间:', roomId, '处理器数量:', handlers.size);
              for (const handler of handlers) {
                handler(stats);
              }
            }
          }
        }
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e);
      }
    };

    newWs.onclose = (event) => {
      isConnectingRef.current = false;
      setStatus('disconnected');
      console.log('[WebSocket] 连接关闭，code:', event.code, 'reason:', event.reason);

      if (event.code !== 1000 && reconnectAttemptRef.current < 5) {
        const delay = Math.pow(2, reconnectAttemptRef.current) * 1000;
        console.log('[WebSocket] 尝试重连，次数:', reconnectAttemptRef.current + 1, '延迟:', delay, 'ms');
        setTimeout(() => {
          reconnectAttemptRef.current++;
          connect();
        }, delay);
      }
    };

    newWs.onerror = (event) => {
      isConnectingRef.current = false;
      setStatus('error');
      console.error('[WebSocket] 连接错误:', event);
    };

    wsRef.current = newWs;
  }, []);

  const send = useCallback((message: WsSubscribeMessage) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    try {
      ws.send(JSON.stringify(message));
    } catch {
      console.warn('WebSocket send failed');
    }
  }, []);

  const subscribe = useCallback((roomId: number, onDanmu: (record: DanmuRecord) => void) => {
    const handlers = danmuHandlersRef.current.get(roomId) || new Set();
    handlers.add(onDanmu);
    danmuHandlersRef.current.set(roomId, handlers);
    console.log('[WebSocket] 添加弹幕处理器，房间:', roomId, '当前处理器数量:', handlers.size);

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.log('[WebSocket] WebSocket 未连接，触发连接');
      connect();
    } else {
      if (!subscribedRoomsRef.current.has(roomId)) {
        send({ type: 'subscribe', roomId });
        subscribedRoomsRef.current.add(roomId);
        console.log('[WebSocket] 发送订阅消息，房间:', roomId);
      } else {
        console.log('[WebSocket] 已订阅房间:', roomId, '跳过重复订阅');
      }
    }
  }, [connect, send]);

  const unsubscribe = useCallback((roomId: number, onDanmu?: (record: DanmuRecord) => void) => {
    if (onDanmu) {
      const handlers = danmuHandlersRef.current.get(roomId);
      if (handlers) {
        handlers.delete(onDanmu);
        if (handlers.size === 0) {
          danmuHandlersRef.current.delete(roomId);
          const statsHandlers = statsHandlersRef.current.get(roomId);
          if (!statsHandlers || statsHandlers.size === 0) {
            subscribedRoomsRef.current.delete(roomId);

            if (statusRef.current === 'connected') {
              send({ type: 'unsubscribe', roomId });
            }
          }
        }
      }
    }
  }, [send]);

  const subscribeStats = useCallback((roomId: number, onStats: (stats: RealtimeStats) => void) => {
    const handlers = statsHandlersRef.current.get(roomId) || new Set();
    handlers.add(onStats);
    statsHandlersRef.current.set(roomId, handlers);
    console.log('[WebSocket] 添加统计处理器，房间:', roomId, '当前处理器数量:', handlers.size);

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.log('[WebSocket] WebSocket 未连接，触发连接');
      connect();
    } else {
      if (!subscribedRoomsRef.current.has(roomId)) {
        send({ type: 'subscribe', roomId });
        subscribedRoomsRef.current.add(roomId);
        console.log('[WebSocket] 发送订阅消息，房间:', roomId);
      } else {
        console.log('[WebSocket] 已订阅房间:', roomId, '跳过重复订阅');
      }
    }
  }, [connect, send]);

  const unsubscribeStats = useCallback((roomId: number, onStats?: (stats: RealtimeStats) => void) => {
    if (onStats) {
      const handlers = statsHandlersRef.current.get(roomId);
      if (handlers) {
        handlers.delete(onStats);
        if (handlers.size === 0) {
          statsHandlersRef.current.delete(roomId);
          const danmuHandlers = danmuHandlersRef.current.get(roomId);
          if (!danmuHandlers || danmuHandlers.size === 0) {
            subscribedRoomsRef.current.delete(roomId);

            if (statusRef.current === 'connected') {
              send({ type: 'unsubscribe', roomId });
            }
          }
        }
      }
    }
  }, [send]);

  useEffect(() => {
    return () => {
      const ws = wsRef.current;
      if (ws) {
        ws.close(1000);
      }
      subscribedRoomsRef.current.clear();
      danmuHandlersRef.current.clear();
      statsHandlersRef.current.clear();
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ subscribe, unsubscribe, subscribeStats, unsubscribeStats, status }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}
