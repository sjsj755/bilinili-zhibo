import React, { useState, useEffect } from 'react';
import { History, Clock, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { sessionApi } from '@/services/api';
import type { DanmuSession, Room } from '@/types';

interface HistoryCardProps {
  room: Room;
  onSessionClick?: (sessionId: number) => void;
  compact?: boolean;
}

export const HistoryCard = React.memo(function HistoryCard({ room, onSessionClick, compact = false }: HistoryCardProps) {
  const [sessions, setSessions] = useState<DanmuSession[]>([]);
  const [expandedSession, setExpandedSession] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!room) return;

    const fetchSessions = async () => {
      setLoading(true);
      try {
        const response = await sessionApi.getList(room.room_id);
        if (response.code === 0 && response.data) {
          setSessions(response.data);
        }
      } catch (error) {
        console.error('Fetch sessions failed:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();

    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, [room]);

  useEffect(() => {
    if (!room) return;
    if (room.status === 'idle' || room.status === 'error') {
      const fetchSessions = async () => {
        try {
          const response = await sessionApi.getList(room.room_id);
          if (response.code === 0 && response.data) {
            setSessions(response.data);
          }
        } catch (error) {
          console.error('Fetch sessions after stop failed:', error);
        }
      };
      fetchSessions();
    }
  }, [room?.status]);

  const handleDelete = async (sessionId: number) => {
    if (!room) return;
    try {
      const response = await sessionApi.delete(room.room_id, sessionId);
      if (response.code === 0) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      }
    } catch (error) {
      console.error('Delete session failed:', error);
    }
  };

  const formatTime = (timeStr: string) => {
    if (!timeStr) return '';
    const date = new Date(timeStr.replace(' ', 'T'));
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timeStr: string) => {
    if (!timeStr) return '';
    const date = new Date(timeStr.replace(' ', 'T'));
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  };

  const getDuration = (start: string, end: string) => {
    if (!end) return '进行中';
    const startTime = new Date(start.replace(' ', 'T')).getTime();
    const endTime = new Date(end.replace(' ', 'T')).getTime();
    const diffMinutes = Math.round((endTime - startTime) / 60000);
    if (diffMinutes < 60) {
      return `${diffMinutes}分钟`;
    }
    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;
    return minutes > 0 ? `${hours}小时${minutes}分钟` : `${hours}小时`;
  };

  if (compact) {
    return (
      <div>
        {loading ? (
          <div className="flex items-center justify-center py-4 text-gray-400">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-4 text-gray-400">
            <History className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">暂无采集记录</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`rounded-lg border ${
                  session.status === 'active'
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-200 bg-gray-50'
                } overflow-hidden`}
              >
                <div 
                  className={`p-3 cursor-pointer hover:bg-gray-100 transition-colors ${
                    onSessionClick ? 'hover:bg-blue-50' : ''
                  }`}
                  onClick={() => {
                    if (onSessionClick) {
                      onSessionClick(session.id);
                    }
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          session.status === 'active'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-200 text-gray-600'
                        }`}>
                          {session.status === 'active' ? '采集中' : '已结束'}
                        </span>
                        <span className="text-sm font-medium text-gray-700">
                          {formatDate(session.start_time)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>{formatTime(session.start_time)}</span>
                        <span>~</span>
                        <span>{formatTime(session.end_time) || '--:--'}</span>
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {session.danmu_count} 条弹幕
                      </div>
                    </div>
                    <button
                      onClick={() => setExpandedSession(expandedSession === session.id ? null : session.id)}
                      className="p-1 hover:bg-gray-200 rounded transition-colors"
                    >
                      {expandedSession === session.id ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                </div>

                {expandedSession === session.id && (
                  <div className="px-3 pb-3">
                    <div className="flex items-center justify-between pt-2 border-t border-gray-200">
                      <span className="text-xs text-gray-500">
                        会话 ID: {session.id}
                      </span>
                      {session.status !== 'active' && (
                        <button
                          onClick={() => handleDelete(session.id)}
                          className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                          删除
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="w-80 bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
          <History className="w-5 h-5" />
          采集历史
        </h2>
        <span className="text-sm text-gray-500">{sessions.length} 次采集</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <History className="w-10 h-10 mb-2 opacity-50" />
            <p className="text-sm">暂无采集记录</p>
            <p className="text-xs mt-1">开始采集后将记录弹幕</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`rounded-lg border ${
                  session.status === 'active'
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-200 bg-gray-50'
                } overflow-hidden`}
              >
                <div 
                  className={`p-3 cursor-pointer hover:bg-gray-100 transition-colors ${
                    onSessionClick ? 'hover:bg-blue-50' : ''
                  }`}
                  onClick={() => {
                    if (onSessionClick) {
                      onSessionClick(session.id);
                    }
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          session.status === 'active'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-200 text-gray-600'
                        }`}>
                          {session.status === 'active' ? '采集中' : '已结束'}
                        </span>
                        <span className="text-sm font-medium text-gray-700">
                          {formatDate(session.start_time)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>{formatTime(session.start_time)}</span>
                        <span>~</span>
                        <span>{formatTime(session.end_time) || '--:--'}</span>
                        <span className="text-gray-400">({getDuration(session.start_time, session.end_time)})</span>
                      </div>
                      <div className="mt-2 text-xs text-gray-500">
                        {session.danmu_count} 条弹幕
                      </div>
                    </div>
                    <button
                      onClick={() => setExpandedSession(expandedSession === session.id ? null : session.id)}
                      className="p-1 hover:bg-gray-200 rounded transition-colors"
                    >
                      {expandedSession === session.id ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                </div>

                {expandedSession === session.id && (
                  <div className="px-3 pb-3">
                    <div className="flex items-center justify-between pt-2 border-t border-gray-200">
                      <span className="text-xs text-gray-500">
                        会话 ID: {session.id}
                      </span>
                      {session.status !== 'active' && (
                        <button
                          onClick={() => handleDelete(session.id)}
                          className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                          删除
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});