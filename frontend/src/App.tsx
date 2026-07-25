import { Routes, Route, useParams } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { Dashboard } from '@/pages/Dashboard';
import { RoomDetail } from '@/pages/RoomDetail';
import { DeepAnalysis } from '@/pages/DeepAnalysis';
import { ReplayManager } from '@/pages/ReplayManager';
import { TestWs } from '@/pages/TestWs';
import { useRoom } from '@/hooks/useRoom';

function MainContent() {
  const { rooms } = useRoom();

  const RoomDetailWithRoom = () => {
    const { roomId } = useParams<{ roomId: string }>();
    const numericId = roomId ? parseInt(roomId, 10) : null;
    const room = rooms.find((r) => r.room_id === numericId) || null;
    return <RoomDetail room={room} />;
  };

  const DeepAnalysisWithRoom = () => {
    const { roomId } = useParams<{ roomId: string }>();
    const numericId = roomId ? parseInt(roomId, 10) : null;
    const room = rooms.find((r) => r.room_id === numericId) || null;
    return <DeepAnalysis room={room} />;
  };

  return (
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/room/:roomId" element={<RoomDetailWithRoom />} />
      <Route path="/room/:roomId/analysis" element={<DeepAnalysisWithRoom />} />
      <Route path="/analysis" element={<DeepAnalysis room={null} />} />
      <Route path="/replay" element={<ReplayManager />} />
      <Route path="/settings" element={<div className="p-6">设置页面开发中...</div>} />
      <Route path="/test-ws" element={<TestWs />} />
      <Route path="/" element={<Dashboard />} />
    </Routes>
  );
}

function App() {
  const getSelectedRoomId = () => {
    const pathname = window.location.pathname;
    const match = pathname.match(/\/room\/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  };

  return (
    <div className="flex">
      <Sidebar selectedRoomId={getSelectedRoomId()} />
      <div className="flex-1 bg-gray-50 min-h-screen">
        <MainContent />
      </div>
    </div>
  );
}

export default App;