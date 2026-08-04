import { Suspense, lazy } from 'react';
import { Routes, Route, useParams } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { useRoom } from '@/hooks/useRoom';

const Dashboard = lazy(() => import('@/pages/Dashboard').then(m => ({ default: m.Dashboard })));
const RoomDetail = lazy(() => import('@/pages/RoomDetail').then(m => ({ default: m.RoomDetail })));
const DeepAnalysis = lazy(() => import('@/pages/DeepAnalysis').then(m => ({ default: m.DeepAnalysis })));
const ReplayManager = lazy(() => import('@/pages/ReplayManager').then(m => ({ default: m.ReplayManager })));
const TestWs = lazy(() => import('@/pages/TestWs').then(m => ({ default: m.TestWs })));

const PageLoading = () => (
  <div className="p-6 flex items-center justify-center h-full min-h-[200px]">
    <div className="text-center text-gray-400">
      <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin mx-auto mb-3"></div>
      <p className="text-sm">加载中...</p>
    </div>
  </div>
);

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
    <Suspense fallback={<PageLoading />}>
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
    </Suspense>
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