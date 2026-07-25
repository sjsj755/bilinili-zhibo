import os
import sys
import logging
import threading
import time
import collections
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger("frequency_engine")


class FrequencyEngine:
    def __init__(self, window_size=10, step_size=1, cleanup_interval=60):
        self.window_size = window_size
        self.step_size = step_size
        self.cleanup_interval = cleanup_interval
        
        self._room_data = {}
        self._lock = threading.Lock()
        self._callbacks = []
        
        self._running = False
        self._thread = None
        self._last_cleanup = time.time()
    
    def _get_or_create_room(self, room_id):
        with self._lock:
            if room_id not in self._room_data:
                self._room_data[room_id] = {
                    "timestamps": collections.deque(),
                    "total_count": 0,
                    "last_update": time.time()
                }
            return self._room_data[room_id]
    
    def add_danmu(self, room_id, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        
        room = self._get_or_create_room(room_id)
        
        with self._lock:
            room["timestamps"].append(timestamp)
            room["total_count"] += 1
            room["last_update"] = time.time()
            
            cutoff = timestamp - self.window_size
            while room["timestamps"] and room["timestamps"][0] < cutoff:
                room["timestamps"].popleft()
    
    def get_frequency(self, room_id):
        with self._lock:
            if room_id not in self._room_data:
                return 0.0
            
            room = self._room_data[room_id]
            count = len(room["timestamps"])
            return round(count / self.window_size, 2)
    
    def get_stats(self, room_id):
        with self._lock:
            if room_id not in self._room_data:
                return {
                    "room_id": room_id,
                    "frequency": 0.0,
                    "count": 0,
                    "total_count": 0,
                    "timestamp": time.time(),
                    "window_start": time.time() - self.window_size,
                    "window_end": time.time()
                }
            
            room = self._room_data[room_id]
            count = len(room["timestamps"])
            now = time.time()
            
            return {
                "room_id": room_id,
                "frequency": round(count / self.window_size, 2),
                "count": count,
                "total_count": room["total_count"],
                "timestamp": now,
                "window_start": now - self.window_size,
                "window_end": now,
                "last_update": room["last_update"]
            }
    
    def get_all_rooms_stats(self):
        with self._lock:
            now = time.time()
            stats_list = []
            
            for room_id, room in self._room_data.items():
                count = len(room["timestamps"])
                stats_list.append({
                    "room_id": room_id,
                    "frequency": round(count / self.window_size, 2),
                    "count": count,
                    "total_count": room["total_count"],
                    "timestamp": now,
                    "window_start": now - self.window_size,
                    "window_end": now,
                    "last_update": room["last_update"]
                })
            
            return stats_list
    
    def _cleanup_stale_rooms(self):
        now = time.time()
        stale_rooms = []
        
        with self._lock:
            for room_id, room in self._room_data.items():
                if now - room["last_update"] > self.cleanup_interval:
                    stale_rooms.append(room_id)
            
            for room_id in stale_rooms:
                del self._room_data[room_id]
                logger.debug(f"清理过期房间数据: {room_id}")
        
        self._last_cleanup = now
    
    def add_callback(self, callback):
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _notify_callbacks(self, stats):
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    def _process_loop(self):
        while self._running:
            try:
                now = time.time()
                
                if now - self._last_cleanup > self.cleanup_interval:
                    self._cleanup_stale_rooms()
                
                stats_list = self.get_all_rooms_stats()
                if stats_list:
                    self._notify_callbacks(stats_list)
                
                time.sleep(self.step_size)
            except Exception as e:
                logger.error(f"处理循环异常: {e}")
                time.sleep(1)
    
    def start(self):
        if self._running:
            logger.warning("频率引擎已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info(f"频率引擎已启动，窗口大小={self.window_size}s，步长={self.step_size}s")
    
    def stop(self):
        if not self._running:
            return
        
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("频率引擎已停止")
    
    def get_room_count(self):
        with self._lock:
            return len(self._room_data)
    
    def reset_room(self, room_id):
        with self._lock:
            if room_id in self._room_data:
                self._room_data[room_id] = {
                    "timestamps": collections.deque(),
                    "total_count": 0,
                    "last_update": time.time()
                }
                logger.debug(f"重置房间数据: {room_id}")
    
    def remove_room(self, room_id):
        with self._lock:
            if room_id in self._room_data:
                del self._room_data[room_id]
                logger.debug(f"移除房间数据: {room_id}")


frequencyEngine = FrequencyEngine()