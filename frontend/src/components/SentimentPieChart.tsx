import React, { useEffect, useRef } from 'react';
import echarts from '@/utils/echarts';
import { PieChart } from 'lucide-react';
import type { RealtimeSentiment } from '@/types';

interface SentimentPieChartProps {
  data: RealtimeSentiment | null;
  height?: string;
}

export const SentimentPieChart: React.FC<SentimentPieChartProps> = ({ data, height = '200px' }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const hasData = data && data.total_count > 0;

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

    const chartData = [
      {
        value: data.positive_count,
        name: '正面',
        itemStyle: { color: '#22c55e' }
      },
      {
        value: data.negative_count,
        name: '负面',
        itemStyle: { color: '#ef4444' }
      },
      {
        value: data.neutral_count,
        name: '中性',
        itemStyle: { color: '#9ca3af' }
      }
    ];

    const totalCount = data.total_count;

    const option: echarts.EChartsCoreOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        textStyle: {
          color: '#374151'
        },
        formatter: (params: any) => {
          const percent = totalCount > 0 ? ((params.value / totalCount) * 100).toFixed(1) : '0.0';
          return `${params.name}<br/>数量: <strong>${params.value}</strong><br/>占比: <strong>${percent}%</strong>`;
        }
      },
      legend: {
        orient: 'horizontal',
        bottom: '5%',
        itemWidth: 10,
        itemHeight: 10,
        textStyle: {
          color: '#6b7280',
          fontSize: 11
        },
        data: ['正面', '负面', '中性']
      },
      series: [
        {
          name: '情感分布',
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['50%', '42%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold',
              formatter: (params: any) => {
                const percent = totalCount > 0 ? ((params.value / totalCount) * 100).toFixed(1) : '0.0';
                return `${params.name}\n${params.value} (${percent}%)`;
              }
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.2)'
            }
          },
          labelLine: {
            show: false
          },
          data: chartData,
          animationDuration: 500,
          animationEasing: 'cubicOut'
        }
      ]
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

  const hasData = data && data.total_count > 0;
  const totalCount = data?.total_count || 0;

  const chartHeight = typeof height === 'string' ? height : '200px';
  const headerHeight = 40;

  return (
    <div className="bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm" style={{ height: chartHeight }}>
      <div className="p-3 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900 flex items-center gap-2">
          <PieChart className="w-4 h-4 text-green-500" />
          情感分布
        </h3>
        <span className="text-xs text-gray-500">{totalCount} 条</span>
      </div>
      <div ref={chartRef} className="w-full" style={{ height: `calc(${chartHeight} - ${headerHeight}px)` }}>
        {!hasData && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <PieChart className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">暂无数据</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SentimentPieChart;