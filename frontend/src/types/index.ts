export interface Room {
  room_id: number;
  room_name: string;
  anchor_name: string;
  status: 'idle' | 'monitoring' | 'error';
  error_msg: string;
  danmu_count: number;
  created_at: string;
  updated_at: string;
}

export interface DanmuRecord {
  id?: number;
  room_id: number;
  session_id?: number;
  uid: number;
  username: string;
  content: string;
  timestamp: number;
  created_at?: string;
  medal_level?: number;
  medal_name?: string;
  user_level?: number;
}

export interface DanmuSession {
  id: number;
  room_id: number;
  start_time: string;
  end_time: string;
  danmu_count: number;
  status: 'active' | 'ended';
  created_at: string;
}

export interface DanmuStats {
  room_id: number;
  total_count: number;
  peak_rate: number;
  avg_rate: number;
  hour_distribution: number[];
}

export interface ApiResponse<T = null> {
  code: number;
  msg: string;
  data: T;
}

export interface DanmuListResponse {
  list: DanmuRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface WsMessage {
  type: string;
  roomId?: number;
  data?: DanmuRecord;
  message?: string;
}

export interface WsSubscribeMessage {
  type: 'subscribe' | 'unsubscribe';
  roomId: number;
}

export interface RealtimeFrequency {
  room_id: number;
  frequency: number;
  count: number;
  total_count: number;
  timestamp: number;
  window_start: number;
  window_end: number;
  last_update: number;
}

export interface RealtimeSentiment {
  room_id: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_count: number;
  positive_rate: number;
  negative_rate: number;
  neutral_rate: number;
}

export interface RealtimeKeyword {
  word: string;
  count: number;
  frequency: number;
}

export interface RealtimeKeywords {
  top_k: RealtimeKeyword[];
  total_count: number;
}

export interface RealtimeStats {
  room_id: number;
  timestamp: number;
  frequency: RealtimeFrequency;
  sentiment: RealtimeSentiment;
  keywords: RealtimeKeywords;
}

export interface WsRealtimeStatsMessage {
  type: 'realtime_stats';
  data: RealtimeStats[];
}
