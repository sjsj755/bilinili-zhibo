import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import echarts from '@/utils/echarts';
import type { RealtimeFrequency } from '@/types';

interface FrequencyChartProps {
  data: RealtimeFrequency[];
  height?: string;
}

interface DataPoint {
  time: string;
  frequency: number;
}

export default function FrequencyChart({ data, height = '250px' }: FrequencyChartProps) {
  const chartData: DataPoint[] = useMemo(() => {
    return data.map(item => ({
      time: new Date(item.timestamp * 1000).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
      frequency: item.frequency
    }));
  }, [data]);

  const currentFrequency = data.length > 0 ? data[data.length - 1].frequency : 0;

  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: {
        color: '#374151'
      },
      formatter: (params: any) => {
        const item = params[0];
        return `${item.name}<br/>弹幕频率: <strong>${item.value}</strong> 条/秒`;
      }
    },
    xAxis: {
      type: 'category',
      data: chartData.map(item => item.time),
      axisLine: {
        lineStyle: {
          color: '#e5e7eb'
        }
      },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11,
        rotate: chartData.length > 20 ? 45 : 0
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: '弹幕/秒',
      nameTextStyle: {
        color: '#9ca3af',
        fontSize: 11
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: '#f3f4f6',
          type: 'dashed'
        }
      },
      min: 0
    },
    series: [
      {
        name: '弹幕频率',
        type: 'line',
        data: chartData.map(item => item.frequency),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 2,
          color: '#6366f1'
        },
        itemStyle: {
          color: '#6366f1',
          borderWidth: 2,
          borderColor: '#fff'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.05)' }
            ]
          }
        },
        animationDuration: 300,
        animationEasing: 'linear'
      }
    ]
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          弹幕频率趋势
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-indigo-600">{currentFrequency.toFixed(1)}</div>
          <div className="text-xs text-gray-400">条/秒</div>
        </div>
      </h3>
      
      {data.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-gray-400">
          <svg className="w-12 h-12 mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">暂无数据</p>
          <p className="text-xs mt-1">开始采集后将显示频率趋势</p>
        </div>
      ) : (
        <ReactECharts
          echarts={echarts}
          option={option}
          style={{ height }}
          opts={{ renderer: 'canvas' }}
          notMerge={true}
        />
      )}
    </div>
  );
}