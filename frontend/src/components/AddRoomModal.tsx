import { useState } from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface AddRoomModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (roomId: number) => Promise<{ code: number; msg: string; data?: unknown }>;
}

export function AddRoomModal({ isOpen, onClose, onAdd }: AddRoomModalProps) {
  const [roomId, setRoomId] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleSubmit = async () => {
    if (!roomId.trim()) {
      setStatus('error');
      setMessage('请输入直播间 ID');
      return;
    }

    const id = parseInt(roomId, 10);
    if (isNaN(id) || id <= 0) {
      setStatus('error');
      setMessage('请输入有效的直播间 ID');
      return;
    }

    setLoading(true);
    setStatus('idle');
    setMessage('');

    try {
      const response = await onAdd(id);
      if (response.code === 0) {
        setStatus('success');
        setMessage(response.msg || '添加成功');
        setRoomId('');
        setTimeout(() => {
          onClose();
        }, 1500);
      } else {
        setStatus('error');
        setMessage(response.msg || '添加失败');
      }
    } catch (e) {
      setStatus('error');
      setMessage('添加房间失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setRoomId('');
    setLoading(false);
    setStatus('idle');
    setMessage('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
        <h3 className="text-lg font-medium text-gray-900 mb-4">添加直播间</h3>
        <input
          type="number"
          value={roomId}
          onChange={(e) => {
            setRoomId(e.target.value);
            setStatus('idle');
            setMessage('');
          }}
          placeholder="输入直播间 ID"
          className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-500"
          disabled={loading}
        />
        {message && (
          <div className={`flex items-center gap-2 mt-3 text-sm ${
            status === 'success' ? 'text-green-600' : 'text-red-500'
          }`}>
            {status === 'success' ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <XCircle className="w-4 h-4" />
            )}
            <span>{message}</span>
          </div>
        )}
        <div className="flex gap-3 mt-4">
          <button
            onClick={handleClose}
            className="flex-1 px-3 py-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            type="button"
            disabled={loading}
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            className="flex-1 px-3 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white transition-colors flex items-center justify-center gap-2"
            type="button"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>添加中...</span>
              </>
            ) : (
              <span>添加</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}