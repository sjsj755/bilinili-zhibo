import React from 'react';
import { Play, Square, Loader2, CheckCircle, XCircle } from 'lucide-react';
import type { Room } from '@/types';

interface RoomHeaderProps {
  room: Room;
  loading: boolean;
  feedback: 'idle' | 'success' | 'error';
  feedbackMsg: string;
  onStartMonitor: () => void;
  onStopMonitor: () => void;
}

export const RoomHeader: React.FC<RoomHeaderProps> = ({
  room,
  loading,
  feedback,
  feedbackMsg,
  onStartMonitor,
  onStopMonitor,
}) => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{room.room_name}</h1>
        <p className="text-gray-500 mt-1">主播: {room.anchor_name}</p>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100">
          <div
            className={`w-2 h-2 rounded-full ${
              room.status === 'monitoring'
                ? 'bg-green-500 animate-pulse'
                : room.status === 'error'
                ? 'bg-red-500'
                : 'bg-gray-400'
            }`}
          />
          <span className="text-sm text-gray-700">
            {room.status === 'monitoring'
              ? '监控中'
              : room.status === 'error'
              ? '错误'
              : '空闲'}
          </span>
        </div>

        {room.status !== 'error' && (
          <div className="flex items-center gap-2">
            {room.status === 'idle' && (
              <button
                onClick={onStartMonitor}
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
                onClick={onStopMonitor}
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
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
              feedback === 'success'
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
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
  );
};

export default RoomHeader;