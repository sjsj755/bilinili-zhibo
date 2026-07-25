import { useRoom } from '@/hooks/useRoom';
import { danmuApi } from '@/services/api';
import React, { useEffect, useState, useMemo } from 'react';
import { TrendingUp, Users, MessageSquare, Activity, BarChart3 } from 'lucide-react';
import type { DanmuStats } from '@/types';

export const Dashboard = React.memo(function Dashboard() {
  const { rooms } = useRoom();
  const [statsMap, setStatsMap] = useState<Map<number, DanmuStats>>(new Map());

  useEffect(() => {
    if (rooms.length === 0) {
      setStatsMap(new Map());
      return;
    }

    const fetchStats = async () => {
      const newStatsMap = new Map<number, DanmuStats>();
      for (const room of rooms) {
        try {
          const response = await danmuApi.getStats(room.room_id);
          if (response.code === 0 && response.data) {
            newStatsMap.set(room.room_id, response.data);
          }
        } catch (e) {
          console.error('Fetch stats failed:', e);
        }
      }
      setStatsMap(newStatsMap);
    };

    const timer = setTimeout(fetchStats, 1000);
    return () => clearTimeout(timer);
  }, [rooms]);

  const totalDanmu = useMemo(() => {
    return rooms.reduce((sum, room) => sum + room.danmu_count, 0);
  }, [rooms]);

  const monitoringRooms = useMemo(() => {
    return rooms.filter((room) => room.status === 'monitoring').length;
  }, [rooms]);

  const maxPeakRate = useMemo(() => {
    let maxRate = 0;
    for (const room of rooms) {
      const rate = statsMap.get(room.room_id)?.peak_rate || 0;
      if (rate > maxRate) maxRate = rate;
    }
    return maxRate;
  }, [rooms, statsMap]);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">首页</h1>
        <p className="text-gray-500 mt-1">实时监控直播间弹幕数据</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">总弹幕数</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{totalDanmu.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-50">
              <MessageSquare className="w-6 h-6 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">监控中房间</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{monitoringRooms}</p>
            </div>
            <div className="p-3 rounded-lg bg-green-50">
              <Activity className="w-6 h-6 text-green-500" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">总房间数</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{rooms.length}</p>
            </div>
            <div className="p-3 rounded-lg bg-purple-50">
              <Users className="w-6 h-6 text-purple-500" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">最高峰值</p>
              <p className="text-2xl font-bold text-orange-500 mt-1">
                {maxPeakRate.toFixed(1)}/s
              </p>
            </div>
            <div className="p-3 rounded-lg bg-orange-50">
              <TrendingUp className="w-6 h-6 text-orange-500" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            实时弹幕频率（最近5分钟）
          </h2>
          <div className="h-64 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>请选择一个监控中的房间查看实时数据</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h2 className="text-lg font-medium text-gray-900 mb-4">房间列表</h2>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {rooms.map((room) => (
              <div
                key={room.room_id}
                className="p-3 rounded-lg bg-gray-50 hover:bg-gray-100 cursor-pointer transition-colors"
                onClick={() => {
                  window.location.href = `/room/${room.room_id}`;
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-gray-900 text-sm font-medium">{room.room_name || `房间 ${room.room_id}`}</span>
                  <div className={`w-2 h-2 rounded-full ${
                    room.status === 'monitoring' ? 'bg-green-500 animate-pulse' :
                    room.status === 'error' ? 'bg-red-500' : 'bg-gray-400'
                  }`} />
                </div>
                <p className="text-xs text-gray-500 mt-1">{room.danmu_count} 条弹幕</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
});