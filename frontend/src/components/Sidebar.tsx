import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, BarChart3, History, Settings, Users } from 'lucide-react';
import { useRoom } from '@/hooks/useRoom';
import { RoomList } from './RoomList';
import { AddRoomModal } from './AddRoomModal';
import type { Room } from '@/types';

interface SidebarProps {
  selectedRoomId: number | null;
}

export function Sidebar({ selectedRoomId }: SidebarProps) {
  const { rooms, loading, addRoom, deleteRoom, startMonitor, stopMonitor } = useRoom();
  const [showAddModal, setShowAddModal] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { icon: LayoutDashboard, label: '首页', path: '/dashboard' },
    { icon: BarChart3, label: '深度分析', path: '/analysis' },
    { icon: History, label: '回放管理', path: '/replay' },
    { icon: Settings, label: '设置', path: '/settings' },
  ];

  const handleRoomSelect = (room: Room) => {
    navigate(`/room/${room.room_id}`);
  };

  const handleStartMonitor = async (roomId: number) => {
    try {
      const response = await startMonitor(roomId);
      return response;
    } catch {
      return { code: -1, msg: '启动采集失败' };
    }
  };

  const handleStopMonitor = async (roomId: number) => {
    try {
      const response = await stopMonitor(roomId);
      return response;
    } catch {
      return { code: -1, msg: '停止采集失败' };
    }
  };

  const handleDeleteRoom = async (roomId: number) => {
    try {
      await deleteRoom(roomId);
      if (selectedRoomId === roomId) {
        navigate('/dashboard');
      }
    } catch {
      alert('删除房间失败');
    }
  };

  const handleAddRoom = async (roomId: number) => {
    const response = await addRoom(roomId);
    return response;
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Users className="w-6 h-6 text-blue-500" />
          <span className="text-lg font-bold text-gray-900">BiliLini</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">弹幕实时分析系统</p>
      </div>

      <nav className="p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = item.path === '/'
            ? ['/', '/dashboard'].includes(location.pathname) || location.pathname.startsWith('/room/')
            : location.pathname === item.path;

          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
              type="button"
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="flex-1 overflow-hidden flex flex-col">
        <RoomList
          rooms={rooms}
          selectedRoomId={selectedRoomId}
          loading={loading}
          onRoomSelect={handleRoomSelect}
          onStartMonitor={handleStartMonitor}
          onStopMonitor={handleStopMonitor}
          onDeleteRoom={handleDeleteRoom}
          onAddRoom={() => setShowAddModal(true)}
        />
      </div>

      <AddRoomModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddRoom}
      />
    </div>
  );
}