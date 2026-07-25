import React from 'react';
import FrequencyChart from './FrequencyChart';
import SentimentPieChart from './SentimentPieChart';
import KeywordCloud from './KeywordCloud';
import type { RealtimeFrequency, RealtimeSentiment, RealtimeKeywords } from '@/types';

interface AnalysisPanelProps {
  frequencyData: RealtimeFrequency[];
  sentimentData: RealtimeSentiment | null;
  keywordData: RealtimeKeywords | null;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  frequencyData,
  sentimentData,
  keywordData,
}) => {
  return (
    <div className="w-[480px] flex flex-col gap-4">
      <FrequencyChart data={frequencyData} height="180px" />
      <div className="grid grid-cols-2 gap-4">
        <SentimentPieChart data={sentimentData} height="200px" />
        <KeywordCloud data={keywordData} />
      </div>
    </div>
  );
};

export default AnalysisPanel;