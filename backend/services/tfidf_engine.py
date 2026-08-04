"""
高性能 TF-IDF 关键词提取引擎 V2

采用两阶段流式计算架构，借鉴 MapReduce 思想优化大规模数据处理。
时间复杂度：O(N + V)，空间复杂度：O(V + K)
"""

import asyncio
import collections
import heapq
import math
from typing import List, Dict, Any, Optional, Tuple


class TfidfEngineV2:
    """
    TF-IDF 关键词提取引擎（优化版）

    核心思想：
    1. Map 阶段 (流式统计): 单次遍历数据，同时计算 TF 和 DF，避免全量加载。
    2. Reduce 阶段 (聚合排序): 基于稀疏字典计算 IDF，使用堆结构提取 Top K。
    """

    def __init__(self, db_handler=None, segment_engine=None,
                 chunk_size: int = 5000, window_minutes: int = 5):
        """
        初始化引擎

        Args:
            db_handler: 数据库处理器，需实现 getDanmuChunkIterator 方法
            segment_engine: 分词引擎，需实现 segment_text 方法
            chunk_size: 分块读取的弹幕数量，用于控制内存占用
            window_minutes: 时间窗口大小（分钟），用于将弹幕划分为文档
        """
        self.db_handler = db_handler
        self.segment_engine = segment_engine
        self.chunk_size = chunk_size
        self.window_minutes = window_minutes

    def _get_time_windows(self, start_time: int, end_time: int) -> List[Tuple[int, int]]:
        """
        将给定的时间范围切分为多个时间窗口（文档）

        Args:
            start_time: 起始时间戳 (秒)
            end_time: 结束时间戳 (秒)

        Returns:
            时间窗口列表: [(window_start, window_end), ...]
        """
        windows = []
        window_seconds = self.window_minutes * 60
        current_start = start_time

        while current_start < end_time:
            current_end = min(current_start + window_seconds, end_time)
            windows.append((current_start, current_end))
            current_start = current_end

        return windows

    async def extract_keywords(self, room_id: int, start_time: int, 
                               end_time: int, top_k: int = 20) -> Dict[str, Any]:
        """
        核心算法：两阶段流式 TF-IDF

        Args:
            room_id: 直播间 ID
            start_time: 起始时间戳
            end_time: 结束时间戳
            top_k: 返回的关键词数量

        Returns:
            包含关键词列表和统计信息的字典
            {
                "keywords": [{"word": "开席", "score": 15.23}, ...],
                "total_danmu": N,
                "doc_count": M,
                "unique_words": V
            }
        """
        # --- 阶段 1: 流式统计 (Map) ---
        # 使用 defaultdict 实现稀疏存储，节省内存
        word_df = collections.defaultdict(int)  # 文档频率：词 -> 包含该词的文档数
        global_tf = collections.defaultdict(int)  # 全局词频最大值：词 -> 最大 TF
        total_danmu = 0  # 总弹幕数

        # 1. 获取时间窗口列表
        windows = self._get_time_windows(start_time, end_time)
        doc_count = len(windows)  # 文档总数

        if doc_count == 0:
            return self._empty_result()

        # 2. 遍历每个时间窗口，流式读取并统计
        for window_start, window_end in windows:
            window_tf = collections.defaultdict(int)  # 当前窗口的词频

            # 异步流式获取当前窗口的弹幕分块
            async for chunk in self.db_handler.getDanmuChunkIterator(
                room_id, window_start, window_end, self.chunk_size
            ):
                # 处理当前分块
                for danmu in chunk:
                    content = danmu.get("content", "")
                    if not content:
                        continue
                        
                    # 分词
                    words = self.segment_engine.segment_text(content)
                    
                    # 更新当前窗口的词频
                    for word in words:
                        window_tf[word] += 1
                
                # 累加总弹幕数
                total_danmu += len(chunk)

            # 当前窗口处理完毕，更新全局统计
            if window_tf:
                # 更新文档频率：出现过的词都 +1
                for word in window_tf:
                    word_df[word] += 1
                
                # 更新全局词频最大值
                for word, count in window_tf.items():
                    if count > global_tf.get(word, 0):
                        global_tf[word] = count

            # 显式释放当前窗口数据，帮助 GC
            del window_tf

        # 无弹幕数据
        if total_danmu == 0:
            return self._empty_result()

        # --- 阶段 2: 聚合排序 (Reduce) ---
        # 1. 计算 IDF (Inverse Document Frequency)
        # 公式: IDF(w) = log( doc_count / (1 + df(w)) )
        # 使用平滑项 1 避免除零错误
        word_idf = {}
        for word, df in word_df.items():
            word_idf[word] = math.log(doc_count / (1 + df))

        # 2. 计算每个词的 TF-IDF 得分
        # TF 使用全局最大 TF 值
        results = []
        for word in global_tf:
            tf = global_tf[word]
            idf = word_idf.get(word, 0)
            score = tf * idf
            results.append((word, score))

        # 3. 使用堆优化的 Top K 提取 (O(V log K))
        # 而不是全量排序 O(V log V)
        if len(results) > top_k:
            top_keywords = heapq.nlargest(top_k, results, key=lambda x: x[1])
        else:
            top_keywords = sorted(results, key=lambda x: x[1], reverse=True)

        # 4. 格式化输出
        formatted_keywords = [
            {"word": word, "score": round(score, 4)}
            for word, score in top_keywords
        ]

        return {
            "keywords": formatted_keywords,
            "total_danmu": total_danmu,
            "doc_count": doc_count,
            "unique_words": len(global_tf),
        }

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            "keywords": [],
            "total_danmu": 0,
            "doc_count": 0,
            "unique_words": 0,
        }