import { BarChart3, TrendingUp, PieChart, Tag } from 'lucide-react';
import type { Room } from '@/types';

interface DeepAnalysisProps {
  room: Room | null;
}

export function DeepAnalysis({ room }: DeepAnalysisProps) {
  if (!room) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-center">
          <BarChart3 className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">请选择一个直播间查看深度分析</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">深度分析</h1>
        <p className="text-gray-500 mt-1">{room.room_name} - 弹幕数据深度分析</p>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            弹幕频率趋势
          </h2>
          <div className="h-64 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>P2 阶段实现</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5" />
            情感分布
          </h2>
          <div className="h-64 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <PieChart className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>P2 阶段实现</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
        <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
          <Tag className="w-5 h-5" />
          关键词云
        </h2>
        <div className="h-64 flex items-center justify-center text-gray-400">
          <div className="text-center">
            <Tag className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>P2 阶段实现</p>
          </div>
        </div>
      </div>
    </div>
  );
}
