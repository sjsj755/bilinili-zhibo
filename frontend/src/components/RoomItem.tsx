import { useState } from 'react';
import { Play, Square, Trash2, Loader2, CheckCircle, XCircle } from 'lucide-react';
import type { Room } from '@/types';

interface RoomItemProps {
  room: Room;
  isSelected: boolean;
  onSelect: (room: Room) => void;
  onStartMonitor: (roomId: number) => Promise<{ code: number; msg: string }>;
  onStopMonitor: (roomId: number) => Promise<{ code: number; msg: string }>;
  onDelete: (roomId: number) => void;
}

export function RoomItem({ room, isSelected, onSelect, onStartMonitor, onStopMonitor, onDelete }: RoomItemProps) {
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<'idle' | 'success' | 'error'>('idle');
  const [feedbackMsg, setFeedbackMsg] = useState('');

  const handleStart = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setLoading(true);
    setFeedback('idle');
    setFeedbackMsg('');

    try {
      const response = await onStartMonitor(room.room_id);
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
  };

  const handleStop = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setLoading(true);
    setFeedback('idle');
    setFeedbackMsg('');

    try {
      const response = await onStopMonitor(room.room_id);
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
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('确定删除该房间？')) {
      onDelete(room.room_id);
    }
  };

  return (
    <div
      className={`p-3 rounded-lg border cursor-pointer transition-all ${
        isSelected
          ? 'bg-blue-50 border-blue-300'
          : 'bg-gray-50 border-gray-200 hover:border-gray-300'
      }`}
      onClick={() => onSelect(room)}
    >
      <div className="flex items-start justify-between mb-1">
        <span className="font-medium text-gray-900 text-sm">{room.room_name || `房间 ${room.room_id}`}</span>
        <div className={`w-2 h-2 rounded-full mt-1.5 ${
          room.status === 'monitoring' ? 'bg-green-500 animate-pulse' :
          room.status === 'error' ? 'bg-red-500' : 'bg-gray-400'
        }`} />
      </div>
      <p className="text-xs text-gray-500 mb-2">{room.anchor_name || '未知主播'}</p>
      <p className="text-xs text-gray-400 mb-2">{room.danmu_count} 条弹幕</p>
      {feedbackMsg && (
        <div className={`flex items-center gap-1 text-xs mb-2 ${
          feedback === 'success' ? 'text-green-600' : 'text-red-500'
        }`}>
          {feedback === 'success' ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <XCircle className="w-3 h-3" />
          )}
          <span>{feedbackMsg}</span>
        </div>
      )}
      <div className="flex gap-1">
        {room.status === 'idle' && (
          <button
            onClick={handleStart}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded text-xs bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>启动中...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3" />
                <span>开始</span>
              </>
            )}
          </button>
        )}
        {room.status === 'monitoring' && (
          <button
            onClick={handleStop}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded text-xs bg-yellow-500 hover:bg-yellow-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>停止中...</span>
              </>
            ) : (
              <>
                <Square className="w-3 h-3" />
                <span>停止</span>
              </>
            )}
          </button>
        )}
        <button
          onClick={handleDelete}
          className="p-1 rounded hover:bg-red-50 text-gray-500 hover:text-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          type="button"
          title="删除房间"
          disabled={loading}
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}