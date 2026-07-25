import { Plus } from 'lucide-react';
import { RoomItem } from './RoomItem';
import type { Room } from '@/types';

interface RoomListProps {
  rooms: Room[];
  selectedRoomId: number | null;
  loading: boolean;
  onRoomSelect: (room: Room) => void;
  onStartMonitor: (roomId: number) => Promise<{ code: number; msg: string }>;
  onStopMonitor: (roomId: number) => Promise<{ code: number; msg: string }>;
  onDeleteRoom: (roomId: number) => void;
  onAddRoom: () => void;
}

export function RoomList({
  rooms,
  selectedRoomId,
  loading,
  onRoomSelect,
  onStartMonitor,
  onStopMonitor,
  onDeleteRoom,
  onAddRoom,
}: RoomListProps) {
  return (
    <div className="p-4 border-t border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-600">直播间列表</h3>
        <button
          onClick={onAddRoom}
          className="p-1 rounded hover:bg-gray-100 text-blue-500 transition-colors"
          type="button"
          title="添加直播间"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 text-sm py-4">加载中...</div>
      ) : rooms.length === 0 ? (
        <div className="text-center text-gray-500 text-sm py-4">暂无直播间</div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {rooms.map((room) => (
            <RoomItem
              key={room.room_id}
              room={room}
              isSelected={selectedRoomId === room.room_id}
              onSelect={onRoomSelect}
              onStartMonitor={onStartMonitor}
              onStopMonitor={onStopMonitor}
              onDelete={onDeleteRoom}
            />
          ))}
        </div>
      )}
    </div>
  );
}