import os
import sys
import logging
import threading
import queue
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import jieba
    jieba_available = True
except ImportError:
    jieba_available = False
    logging.warning("jieba 未安装，分词功能将不可用")

try:
    from services.sentiment_engine import sentimentEngine
    sentiment_available = True
except ImportError:
    sentiment_available = False
    logging.warning("sentiment_engine 不可用，情感分析功能将不可用")

try:
    from services.keyword_engine import keywordEngine
    keyword_available = True
except ImportError:
    keyword_available = False
    logging.warning("keyword_engine 不可用，关键词统计功能将不可用")

try:
    from services.frequency_engine import frequencyEngine
    frequency_available = True
except ImportError:
    frequency_available = False
    logging.warning("frequency_engine 不可用，频率统计功能将不可用")

logger = logging.getLogger("segment_engine")


class SegmentEngine:
    def __init__(self, stopwords_path=None, userdict_path=None, batch_size=20, process_interval=0.1):
        self.stopwords_path = stopwords_path or os.path.join(os.path.dirname(__file__), "../data/stopwords.txt")
        self.userdict_path = userdict_path or os.path.join(os.path.dirname(__file__), "../data/userdict.txt")
        self.batch_size = batch_size
        self.process_interval = process_interval
        self.stopwords = set()
        self.danmu_queue = queue.Queue()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._callbacks = []

        if jieba_available:
            self._load_stopwords()
            self._load_userdict()
            logger.info("分词引擎初始化完成")
        else:
            logger.warning("jieba 不可用，分词引擎未初始化")

    def _load_stopwords(self):
        try:
            with open(self.stopwords_path, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        self.stopwords.add(word)
            logger.info(f"已加载 {len(self.stopwords)} 个停用词")
        except Exception as e:
            logger.error(f"加载停用词失败: {e}")

    def _load_userdict(self):
        try:
            jieba.load_userdict(self.userdict_path)
            logger.info("自定义词典加载完成")
        except Exception as e:
            logger.error(f"加载自定义词典失败: {e}")

    def add_word(self, word, freq=None, tag=None):
        if jieba_available:
            jieba.add_word(word, freq=freq, tag=tag)
            logger.debug(f"添加自定义词: {word}")

    def del_word(self, word):
        if jieba_available:
            jieba.del_word(word)
            logger.debug(f"删除自定义词: {word}")

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
        
        if sentiment_available:
            sentimentEngine.add_danmu(result)
        
        if keyword_available:
            room_id = result.get("room_id")
            words = result.get("words", [])
            if room_id and words:
                keywordEngine.add_words(room_id, words)
        
        if frequency_available:
            room_id = result.get("room_id")
            if room_id:
                frequencyEngine.add_danmu(room_id)

    def add_danmu(self, danmu_record):
        if not jieba_available:
            return
        self.danmu_queue.put(danmu_record)

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
                    results = self._segment_batch(batch)
                    for result in results:
                        self._notify_callbacks(result)

                time.sleep(self.process_interval)
            except Exception as e:
                logger.error(f"处理循环异常: {e}")

    def _segment_batch(self, batch):
        results = []
        for record in batch:
            try:
                text = record.content
                if not text or not isinstance(text, str):
                    continue

                cleaned_text = self._clean_text(text)
                if not cleaned_text:
                    continue

                words = jieba.lcut(cleaned_text)
                filtered_words = [word for word in words if word not in self.stopwords and self._is_valid_word(word)]

                if filtered_words:
                    results.append({
                        "danmu_id": getattr(record, "id", None),
                        "session_id": record.session_id,
                        "room_id": record.room_id,
                        "text": text,
                        "words": filtered_words,
                        "word_count": len(filtered_words)
                    })
            except Exception as e:
                try:
                    logger.error(f"分词处理失败: {e}, content: {record.content}")
                except:
                    logger.error(f"分词处理失败: {e}")
        return results

    def _clean_text(self, text):
        text = text.strip()
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
        return text

    def _is_valid_word(self, word):
        if not word:
            return False
        if len(word) <= 1:
            return False
        if re.match(r"^\d+$", word):
            return False
        return True

    def segment_text(self, text):
        if not jieba_available:
            return {"words": [], "word_count": 0}

        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            return {"words": [], "word_count": 0}

        words = jieba.lcut(cleaned_text)
        filtered_words = [word for word in words if word not in self.stopwords and self._is_valid_word(word)]

        return {
            "text": text,
            "words": filtered_words,
            "word_count": len(filtered_words)
        }

    def start(self):
        if not jieba_available:
            logger.warning("jieba 不可用，无法启动分词引擎")
            return

        if self._running:
            logger.warning("分词引擎已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("分词引擎已启动")

    def stop(self):
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("分词引擎已停止")

    def get_queue_size(self):
        return self.danmu_queue.qsize()


segmentEngine = SegmentEngine()
