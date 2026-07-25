import { History } from 'lucide-react';

export function ReplayManager() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">回放管理</h1>
        <p className="text-gray-500 mt-1">管理已录制的弹幕回放数据</p>
      </div>

      <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
            <History className="w-5 h-5" />
            回放列表
          </h2>
          <button className="px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm transition-colors">
            导出数据
          </button>
        </div>

        <div className="flex items-center justify-center h-64 text-gray-400">
          <div className="text-center">
            <History className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>暂无回放数据</p>
            <p className="text-sm mt-1">开始采集后将自动保存弹幕数据</p>
          </div>
        </div>
      </div>
    </div>
  );
}
