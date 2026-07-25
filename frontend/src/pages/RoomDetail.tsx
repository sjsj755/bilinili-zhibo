import React, { useEffect, useRef, useCallback, useState } from 'react';
import { MessageSquare, Clock, User, Play, Square, Loader2, CheckCircle, XCircle, ChevronDown } from 'lucide-react';
import { danmuApi, roomApi, sessionApi } from '@/services/api';
import { useDanmaku } from '@/hooks/useDanmaku';
import { HistoryCard } from '@/components/HistoryCard';
import FrequencyChart from '@/components/FrequencyChart';
import { useWebSocket } from '@/context/WebSocketContext';
import type { Room, DanmuRecord, RealtimeStats, RealtimeFrequency } from '@/types';

interface RoomDetailProps {
  room: Room | null;
}

function roomDetailPropsEqual(prevProps: RoomDetailProps, nextProps: RoomDetailProps): boolean {
  const prevRoom = prevProps.room;
  const nextRoom = nextProps.room;
  if (!prevRoom && !nextRoom) return true;
  if (!prevRoom || !nextRoom) return false;
  return prevRoom.room_id === nextRoom.room_id && prevRoom.status === nextRoom.status;
}

export const RoomDetail = React.memo(function RoomDetail({ room }: RoomDetailProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);
  const prevDanmakuCountRef = useRef(0);
  console.log('RoomDetail rendering:', room?.room_id, room?.status);
  const { danmakuList, historyCount, setInitialData, clearAndStartNewSession, markAsHistory, wsStatus } = useDanmaku({
    roomId: room?.room_id || null,
    isMonitoring: room?.status === 'monitoring',
  });

  const { subscribeStats, unsubscribeStats } = useWebSocket();
  const [frequencyData, setFrequencyData] = useState<RealtimeFrequency[]>([]);
  const MAX_DATA_POINTS = 60;

  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<'idle' | 'success' | 'error'>('idle');
  const [feedbackMsg, setFeedbackMsg] = useState('');
  const [hasNewDanmaku, setHasNewDanmaku] = useState(false);
  const [newDanmakuCount, setNewDanmakuCount] = useState(0);

  const handleSessionClick = useCallback(async (sessionId: number) => {
    if (!room) return;
    try {
      const response = await sessionApi.getDetail(room.room_id, sessionId);
      if (response.code === 0 && response.data) {
        setInitialData(response.data.danmuList);
      }
    } catch (error) {
      console.error('Fetch session detail failed:', error);
    }
  }, [room, setInitialData]);

  const handleStartMonitor = useCallback(async () => {
    if (!room || loading) return;
    setLoading(true);
    setFeedback('idle');
    setFeedbackMsg('');

    try {
      const response = await roomApi.startMonitor(room.room_id);
      if (response.code === 0) {
        setFeedback('success');
        setFeedbackMsg(response.msg || '采集已启动');
      } else {
        setFeedback('error');
        setFeedbackMsg(response.msg || '启动失败');
      }
    } catch {
      setFeedback('error');
      setFeedbackMsg('启动失败，请检查网络');
    } finally {
      setLoading(false);
      setTimeout(() => {
        setFeedback('idle');
        setFeedbackMsg('');
      }, 2000);
    }
  }, [room, loading]);

  const handleStopMonitor = useCallback(async () => {
    if (!room || loading) return;
    setLoading(true);
    setFeedback('idle');
    setFeedbackMsg('');

    try {
      const response = await roomApi.stopMonitor(room.room_id);
      if (response.code === 0) {
        setFeedback('success');
        setFeedbackMsg(response.msg || '采集已停止');
      } else {
        setFeedback('error');
        setFeedbackMsg(response.msg || '停止失败');
      }
    } catch {
      setFeedback('error');
      setFeedbackMsg('停止失败，请检查网络');
    } finally {
      setLoading(false);
      setTimeout(() => {
        setFeedback('idle');
        setFeedbackMsg('');
      }, 2000);
    }
  }, [room, loading]);

  useEffect(() => {
    if (!room) return;
    console.log('Room status changed:', room.status);
    
    if (room.status === 'monitoring') {
      clearAndStartNewSession();
    } else if (room.status === 'idle') {
      markAsHistory();
    }
  }, [room?.status, clearAndStartNewSession, markAsHistory]);

  useEffect(() => {
    if (!room) return;
    const fetchHistory = async () => {
      try {
        const response = await danmuApi.getList(room.room_id, { page: 1, pageSize: 100 });
        if (response.code === 0 && response.data) {
          setInitialData(response.data.list);
        }
      } catch {
        console.error('Fetch history failed');
      }
    };

    if (room.status === 'idle' && danmakuList.length === 0) {
      fetchHistory();
    }
  }, [room, setInitialData, danmakuList.length]);

  useEffect(() => {
    if (!room) return;

    const handleStats = (stats: RealtimeStats) => {
      setFrequencyData(prev => {
        const newData = [...prev, stats.frequency];
        if (newData.length > MAX_DATA_POINTS) {
          return newData.slice(-MAX_DATA_POINTS);
        }
        return newData;
      });
    };

    subscribeStats(room.room_id, handleStats);

    return () => {
      unsubscribeStats(room.room_id, handleStats);
      setFrequencyData([]);
    };
  }, [room, subscribeStats, unsubscribeStats]);

  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const threshold = 50;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - threshold;
    
    if (isAtBottom) {
      shouldAutoScrollRef.current = true;
      setHasNewDanmaku(false);
      setNewDanmakuCount(0);
    } else {
      shouldAutoScrollRef.current = false;
    }
  }, []);

  useEffect(() => {
    const currentCount = danmakuList.length;
    const diff = currentCount - prevDanmakuCountRef.current;
    
    if (diff > 0) {
      if (shouldAutoScrollRef.current && scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
      } else {
        setHasNewDanmaku(true);
        setNewDanmakuCount((prev) => prev + diff);
      }
    }
    
    prevDanmakuCountRef.current = currentCount;
  }, [danmakuList]);

  const scrollToLatest = useCallback(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
      shouldAutoScrollRef.current = true;
      setHasNewDanmaku(false);
      setNewDanmakuCount(0);
    }
  }, []);

  const renderDanmakuItem = (danmaku: DanmuRecord, isHistory: boolean) => {
    return (
      <div
        key={danmaku.id}
        className={`flex items-start gap-3 p-3 rounded-lg transition-colors ${
          isHistory
            ? 'bg-gray-100 opacity-70'
            : 'bg-gray-50 hover:bg-gray-100'
        }`}
      >
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isHistory ? 'bg-gradient-to-br from-gray-300 to-gray-400' : 'bg-gradient-to-br from-blue-500 to-purple-500'
        }`}>
          <User className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`font-medium text-sm truncate ${isHistory ? 'text-gray-500' : 'text-gray-900'}`}>
              {danmaku.username}
            </span>
            <span className="text-xs flex items-center gap-1 text-gray-400">
              <Clock className="w-3 h-3" />
              {new Date(danmaku.timestamp * 1000).toLocaleTimeString()}
            </span>
            {isHistory && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-gray-200 text-gray-500">历史</span>
            )}
          </div>
          <p className={`text-sm break-words ${isHistory ? 'text-gray-500' : 'text-gray-700'}`}>
            {danmaku.content}
          </p>
        </div>
      </div>
    );
  };

  if (!room) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-center">
          <MessageSquare className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">请选择一个直播间查看详情</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-screen flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{room.room_name}</h1>
          <p className="text-gray-500 mt-1">主播: {room.anchor_name}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100">
            <div className={`w-2 h-2 rounded-full ${
              room.status === 'monitoring' ? 'bg-green-500 animate-pulse' :
              room.status === 'error' ? 'bg-red-500' : 'bg-gray-400'
            }`} />
            <span className="text-sm text-gray-700">
              {room.status === 'monitoring' ? '监控中' :
               room.status === 'error' ? '错误' : '空闲'}
            </span>
          </div>

          {room.status !== 'error' && (
            <div className="flex items-center gap-2">
              {room.status === 'idle' && (
                <button
                  onClick={handleStartMonitor}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>启动中...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      <span>开始采集</span>
                    </>
                  )}
                </button>
              )}
              {room.status === 'monitoring' && (
                <button
                  onClick={handleStopMonitor}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-yellow-500 hover:bg-yellow-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>停止中...</span>
                    </>
                  ) : (
                    <>
                      <Square className="w-4 h-4" />
                      <span>停止采集</span>
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          {feedbackMsg && (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
              feedback === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {feedback === 'success' ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              <span>{feedbackMsg}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex gap-4">
        <div className="flex-1 bg-white rounded-xl overflow-hidden flex flex-col border border-gray-200 shadow-sm">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              实时弹幕
            </h2>
            <div className="flex items-center gap-4">
              <div className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs ${
                wsStatus === 'connected' ? 'bg-green-100 text-green-700' :
                wsStatus === 'connecting' ? 'bg-yellow-100 text-yellow-700' :
                wsStatus === 'error' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${
                  wsStatus === 'connected' ? 'bg-green-500' :
                  wsStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
                  wsStatus === 'error' ? 'bg-red-500' : 'bg-gray-400'
                }`} />
                {wsStatus === 'connected' ? '已连接' :
                 wsStatus === 'connecting' ? '连接中...' :
                 wsStatus === 'error' ? '连接错误' : '未连接'}
              </div>
              <span className="text-sm text-gray-500">共 {danmakuList.length} 条</span>
            </div>
          </div>

          <div
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-4"
          >
            {danmakuList.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <MessageSquare className="w-12 h-12 mb-2 opacity-50" />
                <p>暂无弹幕数据</p>
                <p className="text-sm mt-1">开始采集后将显示实时弹幕</p>
              </div>
            ) : (
              <div className="space-y-2">
                {danmakuList.slice(0, historyCount).map((danmaku) => (
                  renderDanmakuItem(danmaku, true)
                ))}

                {historyCount > 0 && danmakuList.length > historyCount && (
                  <div className="flex items-center gap-4 my-3">
                    <div className="flex-1 h-px bg-gray-300" />
                    <span className="text-xs text-gray-400 px-2">实时采集开始</span>
                    <div className="flex-1 h-px bg-gray-300" />
                  </div>
                )}

                {danmakuList.slice(historyCount).map((danmaku) => (
                  renderDanmakuItem(danmaku, false)
                ))}
              </div>
            )}

            {hasNewDanmaku && (
              <button
                onClick={scrollToLatest}
                className="fixed bottom-8 left-1/2 transform -translate-x-1/2 px-4 py-2 bg-green-500 text-white rounded-full shadow-lg hover:bg-green-600 transition-all duration-300 flex items-center gap-2 z-50 animate-bounce"
              >
                <span className="font-medium">有 {newDanmakuCount} 条新弹幕</span>
                <ChevronDown className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="w-96 flex flex-col gap-4">
          <FrequencyChart data={frequencyData} />
          <HistoryCard room={room} onSessionClick={handleSessionClick} />
        </div>
      </div>
    </div>
  );
}, roomDetailPropsEqual);