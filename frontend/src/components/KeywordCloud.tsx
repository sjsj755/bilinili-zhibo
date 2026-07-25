import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import { Tag } from 'lucide-react';
import type { RealtimeKeywords } from '@/types';

interface KeywordCloudProps {
  data: RealtimeKeywords | null;
}

export const KeywordCloud: React.FC<KeywordCloudProps> = ({ data }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const hasData = data && data.top_k && data.top_k.length > 0;

    if (!hasData) {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
      return;
    }

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const topWords = data.top_k.slice(0, 25);
    
    const chartData = topWords.map(item => ({
      name: item.word,
      value: item.count * 10
    }));

    const colors = ['#22c55e', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899'];

    const option: any = {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          const word = topWords.find(w => w.word === params.name);
          return `<div style="padding: 8px;">
            <div style="font-weight: bold; margin-bottom: 4px;">${params.name}</div>
            <div>出现次数: ${word?.count || 0}</div>
            <div>频率: ${((word?.frequency || 0) * 100).toFixed(2)}%</div>
          </div>`;
        }
      },
      series: [{
        type: 'wordCloud',
        gridSize: 8,
        sizeRange: [12, 48],
        rotationRange: [-90, 90],
        rotationStep: 45,
        shape: 'circle',
        width: '100%',
        height: '100%',
        drawOutOfBound: false,
        textStyle: {
          fontFamily: 'Microsoft YaHei, sans-serif',
          fontWeight: 'bold',
          color: () => colors[Math.floor(Math.random() * colors.length)]
        },
        emphasis: {
          textStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        data: chartData
      }]
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  const hasData = data && data.top_k && data.top_k.length > 0;

  return (
    <div className="bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm" style={{ height: '200px' }}>
      <div className="p-3 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-900 flex items-center gap-2">
          <Tag className="w-4 h-4 text-purple-500" />
          关键词词云
        </h3>
      </div>
      <div ref={chartRef} className="w-full" style={{ height: 'calc(200px - 40px)' }}>
        {!hasData && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Tag className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">暂无关键词数据</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default KeywordCloud;