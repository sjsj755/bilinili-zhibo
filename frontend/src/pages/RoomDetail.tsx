import React, { useEffect, useRef, useCallback, useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { danmuApi, sessionApi } from '@/services/api';
import { useDanmaku } from '@/hooks/useDanmaku';
import { HistoryCard } from '@/components/HistoryCard';
import RoomHeader from '@/components/RoomHeader';
import DanmakuContainer from '@/components/DanmakuContainer';
import AnalysisPanel from '@/components/AnalysisPanel';
import CollapsiblePanel from '@/components/CollapsiblePanel';
import { useWebSocket } from '@/context/WebSocketContext';
import type { Room, RealtimeStats, RealtimeFrequency, RealtimeSentiment, RealtimeKeywords } from '@/types';

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

  const { danmakuList, historyCount, setInitialData, clearAndStartNewSession, markAsHistory, wsStatus } = useDanmaku({
    roomId: room?.room_id || null,
    isMonitoring: room?.status === 'monitoring',
  });

  const { subscribeStats, unsubscribeStats } = useWebSocket();
  const [frequencyData, setFrequencyData] = useState<RealtimeFrequency[]>([]);
  const [sentimentData, setSentimentData] = useState<RealtimeSentiment | null>(null);
  const [keywordData, setKeywordData] = useState<RealtimeKeywords | null>(null);
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
      const response = await fetch(`/api/rooms/${room.room_id}/monitor`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.code === 0) {
        setFeedback('success');
        setFeedbackMsg(data.msg || '采集已启动');
      } else {
        setFeedback('error');
        setFeedbackMsg(data.msg || '启动失败');
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
      const response = await fetch(`/api/rooms/${room.room_id}/monitor/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.code === 0) {
        setFeedback('success');
        setFeedbackMsg(data.msg || '采集已停止');
      } else {
        setFeedback('error');
        setFeedbackMsg(data.msg || '停止失败');
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

      if (stats.sentiment) {
        setSentimentData(stats.sentiment);
      }

      if (stats.keywords) {
        setKeywordData(stats.keywords);
      }
    };

    subscribeStats(room.room_id, handleStats);

    return () => {
      unsubscribeStats(room.room_id, handleStats);
      setFrequencyData([]);
      setSentimentData(null);
      setKeywordData(null);
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
    <div className="p-6 flex flex-col gap-4">
      <RoomHeader
        room={room}
        loading={loading}
        feedback={feedback}
        feedbackMsg={feedbackMsg}
        onStartMonitor={handleStartMonitor}
        onStopMonitor={handleStopMonitor}
      />

      <CollapsiblePanel title="采集历史" defaultOpen={false}>
        <HistoryCard room={room} onSessionClick={handleSessionClick} compact />
      </CollapsiblePanel>

      <div className="flex gap-4 flex-1">
        <div className="flex-1">
          <DanmakuContainer
            danmakuList={danmakuList}
            historyCount={historyCount}
            wsStatus={wsStatus}
            hasNewDanmaku={hasNewDanmaku}
            newDanmakuCount={newDanmakuCount}
            onScroll={handleScroll}
            onScrollToLatest={scrollToLatest}
          />
        </div>

        <AnalysisPanel
          frequencyData={frequencyData}
          sentimentData={sentimentData}
          keywordData={keywordData}
        />
      </div>
    </div>
  );
}, roomDetailPropsEqual);