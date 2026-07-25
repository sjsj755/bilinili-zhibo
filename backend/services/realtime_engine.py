import os
import sys
import logging
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger("realtime_engine")


class RealtimeAnalyzer:
    def __init__(self, update_interval=1, window_size=60):
        self.update_interval = update_interval
        self.window_size = window_size
        
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._callbacks = []
        
        self._segment_engine = None
        self._sentiment_engine = None
        self._frequency_engine = None
        self._keyword_engine = None
    
    def register_segment_engine(self, engine):
        self._segment_engine = engine
        logger.info("分词引擎已注册")
    
    def register_sentiment_engine(self, engine):
        self._sentiment_engine = engine
        logger.info("情感引擎已注册")
    
    def register_frequency_engine(self, engine):
        self._frequency_engine = engine
        logger.info("频率引擎已注册")
    
    def register_keyword_engine(self, engine):
        self._keyword_engine = engine
        logger.info("关键词引擎已注册")
    
    def _aggregate_analysis(self, room_id):
        now = time.time()
        result = {
            "room_id": room_id,
            "timestamp": now,
            "frequency": None,
            "sentiment": None,
            "keywords": None
        }
        
        if self._frequency_engine:
            result["frequency"] = self._frequency_engine.get_stats(room_id)
        
        if self._sentiment_engine:
            result["sentiment"] = self._sentiment_engine.get_sentiment_stats(room_id)
        
        if self._keyword_engine:
            result["keywords"] = self._keyword_engine.get_top_k(room_id)
        
        return result
    
    def get_analysis(self, room_id):
        return self._aggregate_analysis(room_id)
    
    def get_all_analysis(self):
        room_ids = set()
        
        if self._frequency_engine:
            room_ids.update(self._frequency_engine._room_data.keys())
        if self._sentiment_engine:
            room_ids.update(self._sentiment_engine._room_stats.keys())
        if self._keyword_engine:
            room_ids.update(self._keyword_engine._room_data.keys())
        
        return [self._aggregate_analysis(room_id) for room_id in room_ids]
    
    def add_callback(self, callback):
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _notify_callbacks(self, data):
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    def _process_loop(self):
        while self._running:
            try:
                analysis_list = self.get_all_analysis()
                
                if analysis_list:
                    self._notify_callbacks(analysis_list)
                
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"处理循环异常: {e}")
                time.sleep(1)
    
    def start(self):
        if self._running:
            logger.warning("实时分析引擎已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info(f"实时分析引擎已启动，更新间隔={self.update_interval}s")
    
    def stop(self):
        if not self._running:
            return
        
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("实时分析引擎已停止")
    
    def start_all_engines(self):
        if self._segment_engine:
            self._segment_engine.start()
        
        if self._sentiment_engine:
            self._sentiment_engine.start()
        
        if self._frequency_engine:
            self._frequency_engine.start()
        
        if self._keyword_engine:
            self._keyword_engine.start()
        
        self.start()
        logger.info("所有引擎已启动")
    
    def stop_all_engines(self):
        self.stop()
        
        if self._keyword_engine:
            self._keyword_engine.stop()
        
        if self._frequency_engine:
            self._frequency_engine.stop()
        
        if self._sentiment_engine:
            self._sentiment_engine.stop()
        
        if self._segment_engine:
            self._segment_engine.stop()
        
        logger.info("所有引擎已停止")
    
    def reset_room(self, room_id):
        if self._frequency_engine:
            self._frequency_engine.reset_room(room_id)
        
        if self._sentiment_engine:
            self._sentiment_engine.reset_room(room_id)
        
        if self._keyword_engine:
            self._keyword_engine.reset_room(room_id)
        
        logger.debug(f"重置房间分析数据: {room_id}")
    
    def remove_room(self, room_id):
        if self._frequency_engine:
            self._frequency_engine.remove_room(room_id)
        
        if self._sentiment_engine:
            self._sentiment_engine.remove_room(room_id)
        
        if self._keyword_engine:
            self._keyword_engine.remove_room(room_id)
        
        logger.debug(f"移除房间分析数据: {room_id}")
    
    def get_engine_status(self):
        return {
            "segment_engine": self._segment_engine is not None,
            "sentiment_engine": self._sentiment_engine is not None,
            "frequency_engine": self._frequency_engine is not None,
            "keyword_engine": self._keyword_engine is not None,
            "running": self._running
        }


realtimeAnalyzer = RealtimeAnalyzer()