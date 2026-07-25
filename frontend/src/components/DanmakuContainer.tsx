import React, { useRef } from 'react';
import { MessageSquare, ChevronDown } from 'lucide-react';
import DanmakuItem from './DanmakuItem';
import type { DanmuRecord } from '@/types';

interface DanmakuContainerProps {
  danmakuList: DanmuRecord[];
  historyCount: number;
  wsStatus: 'connected' | 'connecting' | 'disconnected' | 'error';
  hasNewDanmaku: boolean;
  newDanmakuCount: number;
  onScroll: () => void;
  onScrollToLatest: () => void;
}

export const DanmakuContainer: React.FC<DanmakuContainerProps> = ({
  danmakuList,
  historyCount,
  wsStatus,
  hasNewDanmaku,
  newDanmakuCount,
  onScroll,
  onScrollToLatest,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  return (
    <>
      <div
        className="bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm"
        style={{ height: '500px' }}
      >
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            实时弹幕
          </h2>
          <div className="flex items-center gap-4">
            <div
              className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs ${
                wsStatus === 'connected'
                  ? 'bg-green-100 text-green-700'
                  : wsStatus === 'connecting'
                  ? 'bg-yellow-100 text-yellow-700'
                  : wsStatus === 'error'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  wsStatus === 'connected'
                    ? 'bg-green-500'
                    : wsStatus === 'connecting'
                    ? 'bg-yellow-500 animate-pulse'
                    : wsStatus === 'error'
                    ? 'bg-red-500'
                    : 'bg-gray-400'
                }`}
              />
              {wsStatus === 'connected'
                ? '已连接'
                : wsStatus === 'connecting'
                ? '连接中...'
                : wsStatus === 'error'
                ? '连接错误'
                : '未连接'}
            </div>
            <span className="text-sm text-gray-500">共 {danmakuList.length} 条</span>
          </div>
        </div>

        <div
          ref={scrollContainerRef}
          onScroll={onScroll}
          className="h-[calc(500px-60px)] overflow-y-auto p-4"
        >
          {danmakuList.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <MessageSquare className="w-12 h-12 mb-2 opacity-50" />
              <p>暂无弹幕数据</p>
              <p className="text-sm mt-1">开始采集后将显示实时弹幕</p>
            </div>
          ) : (
            <div className="space-y-2">
              {danmakuList.slice(0, historyCount).map((danmaku) => (
                <DanmakuItem key={danmaku.id} danmaku={danmaku} isHistory />
              ))}

              {historyCount > 0 && danmakuList.length > historyCount && (
                <div className="flex items-center gap-4 my-3">
                  <div className="flex-1 h-px bg-gray-300" />
                  <span className="text-xs text-gray-400 px-2">历史弹幕结束</span>
                  <div className="flex-1 h-px bg-gray-300" />
                </div>
              )}

              {danmakuList.slice(historyCount).map((danmaku) => (
                <DanmakuItem key={danmaku.id} danmaku={danmaku} isHistory={false} />
              ))}
            </div>
          )}
        </div>
      </div>

      {hasNewDanmaku && (
        <button
          onClick={onScrollToLatest}
          className="mt-3 w-full px-4 py-2 bg-green-500 text-white rounded-lg shadow hover:bg-green-600 transition-all duration-300 flex items-center justify-center gap-2"
        >
          <span className="font-medium">有 {newDanmakuCount} 条新弹幕</span>
          <ChevronDown className="w-4 h-4" />
        </button>
      )}
    </>
  );
};

export default DanmakuContainer;