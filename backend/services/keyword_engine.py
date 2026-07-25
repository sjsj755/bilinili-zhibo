import os
import sys
import logging
import threading
import time
import collections
import heapq
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger("keyword_engine")


class KeywordEngine:
    def __init__(self, window_size=60, top_k=50, update_interval=1,
                 min_word_length=2, min_frequency=2, cleanup_interval=120):
        self.window_size = window_size
        self.top_k = top_k
        self.update_interval = update_interval
        self.min_word_length = min_word_length
        self.min_frequency = min_frequency
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
                    "word_counts": collections.defaultdict(int),
                    "timestamps": collections.deque(),
                    "top_k_cache": [],
                    "total_count": 0,
                    "last_update": time.time(),
                    "needs_update": False
                }
            return self._room_data[room_id]
    
    def _is_valid_word(self, word):
        if not word:
            return False
        if len(word) < self.min_word_length:
            return False
        if word.isdigit():
            return False
        return True
    
    def add_words(self, room_id, words, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        
        room = self._get_or_create_room(room_id)
        valid_words = [w for w in words if self._is_valid_word(w)]
        
        if not valid_words:
            return
        
        with self._lock:
            for word in valid_words:
                room["word_counts"][word] += 1
                room["total_count"] += 1
            
            room["timestamps"].append((timestamp, valid_words))
            room["last_update"] = time.time()
            room["needs_update"] = True
            
            cutoff = timestamp - self.window_size
            while room["timestamps"] and room["timestamps"][0][0] < cutoff:
                old_timestamp, old_words = room["timestamps"].popleft()
                for word in old_words:
                    room["word_counts"][word] -= 1
                    room["total_count"] -= 1
                    if room["word_counts"][word] <= 0:
                        del room["word_counts"][word]
                room["needs_update"] = True
    
    def _compute_top_k(self, room):
        if not room["word_counts"]:
            return []
        
        candidates = [(-count, word) for word, count in room["word_counts"].items()
                      if count >= self.min_frequency]
        
        heapq.heapify(candidates)
        
        top_k = []
        seen = set()
        
        while candidates and len(top_k) < self.top_k:
            neg_count, word = heapq.heappop(candidates)
            if word not in seen:
                seen.add(word)
                top_k.append((word, -neg_count))
        
        return top_k
    
    def get_top_k(self, room_id):
        with self._lock:
            if room_id not in self._room_data:
                return {
                    "room_id": room_id,
                    "top_k": [],
                    "total_count": 0,
                    "timestamp": time.time(),
                    "window_start": time.time() - self.window_size,
                    "window_end": time.time()
                }
            
            room = self._room_data[room_id]
            
            if room["needs_update"]:
                room["top_k_cache"] = self._compute_top_k(room)
                room["needs_update"] = False
            
            now = time.time()
            total_count = room["total_count"]
            
            top_k_result = []
            for word, count in room["top_k_cache"]:
                frequency = round(count / total_count, 4) if total_count > 0 else 0.0
                top_k_result.append({
                    "word": word,
                    "count": count,
                    "frequency": frequency
                })
            
            return {
                "room_id": room_id,
                "top_k": top_k_result,
                "total_count": total_count,
                "timestamp": now,
                "window_start": now - self.window_size,
                "window_end": now,
                "last_update": room["last_update"]
            }
    
    def get_all_rooms_top_k(self):
        with self._lock:
            now = time.time()
            results = []
            
            for room_id, room in self._room_data.items():
                if room["needs_update"]:
                    room["top_k_cache"] = self._compute_top_k(room)
                    room["needs_update"] = False
                
                total_count = room["total_count"]
                top_k_result = []
                
                for word, count in room["top_k_cache"]:
                    frequency = round(count / total_count, 4) if total_count > 0 else 0.0
                    top_k_result.append({
                        "word": word,
                        "count": count,
                        "frequency": frequency
                    })
                
                results.append({
                    "room_id": room_id,
                    "top_k": top_k_result,
                    "total_count": total_count,
                    "timestamp": now,
                    "window_start": now - self.window_size,
                    "window_end": now,
                    "last_update": room["last_update"]
                })
            
            return results
    
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
                
                stats_list = self.get_all_rooms_top_k()
                if stats_list:
                    self._notify_callbacks(stats_list)
                
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"处理循环异常: {e}")
                time.sleep(1)
    
    def start(self):
        if self._running:
            logger.warning("关键词引擎已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info(f"关键词引擎已启动，窗口大小={self.window_size}s，Top K={self.top_k}")
    
    def stop(self):
        if not self._running:
            return
        
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("关键词引擎已停止")
    
    def get_room_count(self):
        with self._lock:
            return len(self._room_data)
    
    def get_word_count(self, room_id):
        with self._lock:
            if room_id not in self._room_data:
                return 0
            return len(self._room_data[room_id]["word_counts"])
    
    def reset_room(self, room_id):
        with self._lock:
            if room_id in self._room_data:
                self._room_data[room_id] = {
                    "word_counts": collections.defaultdict(int),
                    "timestamps": collections.deque(),
                    "top_k_cache": [],
                    "total_count": 0,
                    "last_update": time.time(),
                    "needs_update": False
                }
                logger.debug(f"重置房间数据: {room_id}")
    
    def remove_room(self, room_id):
        with self._lock:
            if room_id in self._room_data:
                del self._room_data[room_id]
                logger.debug(f"移除房间数据: {room_id}")


keywordEngine = KeywordEngine()