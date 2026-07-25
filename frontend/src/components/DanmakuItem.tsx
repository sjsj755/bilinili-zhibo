import React from 'react';
import { Clock, User } from 'lucide-react';
import type { DanmuRecord } from '@/types';

interface DanmakuItemProps {
  danmaku: DanmuRecord;
  isHistory: boolean;
}

export const DanmakuItem: React.FC<DanmakuItemProps> = ({ danmaku, isHistory }) => {
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg transition-colors ${
        isHistory ? 'bg-gray-100 opacity-70' : 'bg-gray-50 hover:bg-gray-100'
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isHistory
            ? 'bg-gradient-to-br from-gray-300 to-gray-400'
            : 'bg-gradient-to-br from-blue-500 to-purple-500'
        }`}
      >
        <User className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={`font-medium text-sm truncate ${
              isHistory ? 'text-gray-500' : 'text-gray-900'
            }`}
          >
            {danmaku.username}
          </span>
          <span className="text-xs flex items-center gap-1 text-gray-400">
            <Clock className="w-3 h-3" />
            {new Date(danmaku.timestamp * 1000).toLocaleTimeString()}
          </span>
          {isHistory && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-gray-200 text-gray-500">
              历史
            </span>
          )}
        </div>
        <p
          className={`text-sm break-words ${
            isHistory ? 'text-gray-500' : 'text-gray-700'
          }`}
        >
          {danmaku.content}
        </p>
      </div>
    </div>
  );
};

export default DanmakuItem;