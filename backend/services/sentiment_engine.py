import os
import sys
import logging
import threading
import queue
import time
import re
import collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from snownlp import SnowNLP
    from snownlp import sentiment as snownlp_sentiment
    snownlp_available = True
except ImportError:
    snownlp_available = False
    logging.warning("snownlp 未安装，情感分析功能将不可用")

logger = logging.getLogger("sentiment_engine")


class SentimentEngine:
    def __init__(self, pos_path=None, neg_path=None, model_path=None,
                 batch_size=20, process_interval=0.1,
                 positive_threshold=0.6, negative_threshold=0.4,
                 window_size=60, cleanup_interval=120):
        self.pos_path = pos_path or os.path.join(os.path.dirname(__file__), "../data/sentiment_pos.txt")
        self.neg_path = neg_path or os.path.join(os.path.dirname(__file__), "../data/sentiment_neg.txt")
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), "../data/sentiment_model.marshal")
        self.batch_size = batch_size
        self.process_interval = process_interval
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold
        self.window_size = window_size
        self.cleanup_interval = cleanup_interval
        
        self.danmu_queue = queue.Queue()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._callbacks = []
        
        self._model_loaded = False
        
        self._room_stats = {}
        
        if snownlp_available:
            self._init_model()
            logger.info("情感引擎初始化完成")
        else:
            logger.warning("snownlp 不可用，情感引擎未初始化")
    
    def _init_model(self):
        try:
            if os.path.exists(self.model_path):
                snownlp_sentiment.load(self.model_path)
                self._model_loaded = True
                logger.info(f"已加载自定义情感模型: {self.model_path}")
            else:
                logger.info("未找到自定义模型，使用默认模型")
        except Exception as e:
            logger.error(f"加载情感模型失败: {e}")
    
    def train_model(self):
        if not snownlp_available:
            logger.warning("snownlp 不可用，无法训练模型")
            return False
        
        if not os.path.exists(self.pos_path):
            logger.error(f"正面训练数据不存在: {self.pos_path}")
            return False
        
        if not os.path.exists(self.neg_path):
            logger.error(f"负面训练数据不存在: {self.neg_path}")
            return False
        
        try:
            logger.info("开始训练情感模型...")
            snownlp_sentiment.train(self.neg_path, self.pos_path)
            snownlp_sentiment.save(self.model_path)
            self._model_loaded = True
            logger.info(f"情感模型训练完成，已保存至: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"训练情感模型失败: {e}")
            return False
    
    def _get_sentiment_label(self, score):
        if score >= self.positive_threshold:
            return "positive"
        elif score <= self.negative_threshold:
            return "negative"
        else:
            return "neutral"
    
    def analyze(self, text):
        if not snownlp_available:
            return {"score": 0.5, "label": "neutral", "text": text}
        
        if not text or not isinstance(text, str):
            return {"score": 0.5, "label": "neutral", "text": text}
        
        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            return {"score": 0.5, "label": "neutral", "text": text}
        
        try:
            s = SnowNLP(cleaned_text)
            score = float(s.sentiments)
            label = self._get_sentiment_label(score)
            
            return {
                "text": text,
                "score": round(score, 4),
                "label": label
            }
        except Exception as e:
            logger.error(f"情感分析失败: {e}, text: {text}")
            return {"score": 0.5, "label": "neutral", "text": text}
    
    def analyze_batch(self, batch):
        results = []
        for item in batch:
            if isinstance(item, str):
                text = item
                record_id = None
                session_id = None
                room_id = None
            else:
                text = item.get("text", "")
                record_id = item.get("danmu_id")
                session_id = item.get("session_id")
                room_id = item.get("room_id")
            
            result = self.analyze(text)
            
            if record_id is not None:
                result["danmu_id"] = record_id
            if session_id is not None:
                result["session_id"] = session_id
            if room_id is not None:
                result["room_id"] = room_id
            
            results.append(result)
        
        return results
    
    def _clean_text(self, text):
        text = text.strip()
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：]", "", text)
        return text
    
    def _get_or_create_room_stats(self, room_id):
        with self._lock:
            if room_id not in self._room_stats:
                self._room_stats[room_id] = {
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "total_count": 0,
                    "timestamps": collections.deque(),
                    "last_update": time.time()
                }
            return self._room_stats[room_id]
    
    def _update_room_stats(self, room_id, label, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        
        room = self._get_or_create_room_stats(room_id)
        
        with self._lock:
            if label == "positive":
                room["positive_count"] += 1
            elif label == "negative":
                room["negative_count"] += 1
            else:
                room["neutral_count"] += 1
            room["total_count"] += 1
            room["timestamps"].append((timestamp, label))
            room["last_update"] = time.time()
            
            cutoff = timestamp - self.window_size
            while room["timestamps"] and room["timestamps"][0][0] < cutoff:
                old_timestamp, old_label = room["timestamps"].popleft()
                if old_label == "positive":
                    room["positive_count"] -= 1
                elif old_label == "negative":
                    room["negative_count"] -= 1
                else:
                    room["neutral_count"] -= 1
                room["total_count"] -= 1
    
    def get_sentiment_stats(self, room_id):
        with self._lock:
            if room_id not in self._room_stats:
                return {
                    "room_id": room_id,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "total_count": 0,
                    "positive_rate": 0.0,
                    "negative_rate": 0.0,
                    "neutral_rate": 0.0,
                    "timestamp": time.time()
                }
            
            room = self._room_stats[room_id]
            total = room["total_count"] or 1
            
            return {
                "room_id": room_id,
                "positive_count": room["positive_count"],
                "negative_count": room["negative_count"],
                "neutral_count": room["neutral_count"],
                "total_count": room["total_count"],
                "positive_rate": round(room["positive_count"] / total, 4),
                "negative_rate": round(room["negative_count"] / total, 4),
                "neutral_rate": round(room["neutral_count"] / total, 4),
                "timestamp": time.time(),
                "last_update": room["last_update"]
            }
    
    def get_all_rooms_stats(self):
        with self._lock:
            now = time.time()
            results = []
            
            for room_id, room in self._room_stats.items():
                total = room["total_count"] or 1
                results.append({
                    "room_id": room_id,
                    "positive_count": room["positive_count"],
                    "negative_count": room["negative_count"],
                    "neutral_count": room["neutral_count"],
                    "total_count": room["total_count"],
                    "positive_rate": round(room["positive_count"] / total, 4),
                    "negative_rate": round(room["negative_count"] / total, 4),
                    "neutral_rate": round(room["neutral_count"] / total, 4),
                    "timestamp": now,
                    "last_update": room["last_update"]
                })
            
            return results
    
    def _cleanup_stale_rooms(self):
        now = time.time()
        stale_rooms = []
        
        with self._lock:
            for room_id, room in self._room_stats.items():
                if now - room["last_update"] > self.cleanup_interval:
                    stale_rooms.append(room_id)
            
            for room_id in stale_rooms:
                del self._room_stats[room_id]
                logger.debug(f"清理过期房间情感数据: {room_id}")
    
    def add_danmu(self, danmu_record):
        if not snownlp_available:
            return
        self.danmu_queue.put(danmu_record)
    
    def add_callback(self, callback):
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _notify_callbacks(self, result):
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
        
        room_id = result.get("room_id")
        label = result.get("label")
        if room_id and label:
            self._update_room_stats(room_id, label)
    
    def _process_loop(self):
        while self._running:
            try:
                batch = []
                while len(batch) < self.batch_size:
                    try:
                        item = self.danmu_queue.get(timeout=self.process_interval)
                        batch.append(item)
                    except queue.Empty:
                        break
                
                if batch:
                    results = self.analyze_batch(batch)
                    for result in results:
                        self._notify_callbacks(result)
                
                if time.time() - self._last_cleanup > self.cleanup_interval:
                    self._cleanup_stale_rooms()
                    self._last_cleanup = time.time()
                
                time.sleep(self.process_interval)
            except Exception as e:
                logger.error(f"处理循环异常: {e}")
    
    def start(self):
        if not snownlp_available:
            logger.warning("snownlp 不可用，无法启动情感引擎")
            return
        
        if self._running:
            logger.warning("情感引擎已在运行")
            return
        
        self._running = True
        self._last_cleanup = time.time()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("情感引擎已启动")
    
    def stop(self):
        if not self._running:
            return
        
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("情感引擎已停止")
    
    def get_queue_size(self):
        return self.danmu_queue.qsize()
    
    def set_thresholds(self, positive_threshold, negative_threshold):
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold
        logger.info(f"阈值已更新: 正面阈值={positive_threshold}, 负面阈值={negative_threshold}")
    
    def reset_room(self, room_id):
        with self._lock:
            if room_id in self._room_stats:
                self._room_stats[room_id] = {
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "total_count": 0,
                    "timestamps": collections.deque(),
                    "last_update": time.time()
                }
                logger.debug(f"重置房间情感数据: {room_id}")
    
    def remove_room(self, room_id):
        with self._lock:
            if room_id in self._room_stats:
                del self._room_stats[room_id]
                logger.debug(f"移除房间情感数据: {room_id}")


sentimentEngine = SentimentEngine()