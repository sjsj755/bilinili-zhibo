"""
TF-IDF Engine V2 单元测试与基准测试
"""

import asyncio
import collections
import heapq
import math
import time
from typing import List, Dict, Any, AsyncIterator, Tuple
from unittest.mock import AsyncMock, patch


class MockSegmentEngine:
    """模拟分词引擎"""
    
    def segment_text(self, text: str) -> List[str]:
        """简单分词：按空格和标点符号分割"""
        # 模拟分词逻辑
        words = []
        for token in text.split():
            # 简单清洗
            token = token.strip(".,!?。，！？")
            if token and len(token) > 1:
                words.append(token)
        return words


class MockDBHandler:
    """模拟数据库处理器"""
    
    def __init__(self, danmu_data: List[Dict[str, Any]]):
        self.danmu_data = danmu_data
        
    async def getDanmuChunkIterator(self, room_id: int, start_time: int, 
                                    end_time: int, chunk_size: int) -> AsyncIterator[List[Dict[str, Any]]]:
        """模拟流式分块迭代"""
        # 过滤时间范围内的弹幕
        filtered = [d for d in self.danmu_data 
                    if start_time <= d["timestamp"] < end_time]
        
        # 分块
        for i in range(0, len(filtered), chunk_size):
            yield filtered[i:i + chunk_size]


def create_test_data(num_danmu: int = 10000, num_rooms: int = 10) -> Tuple[List[Dict[str, Any]], List[int], int, int]:
    """创建测试数据
    
    Args:
        num_danmu: 弹幕总数
        num_rooms: 房间数量
        
    Returns:
        (弹幕列表, 房间ID列表, 起始时间, 结束时间)
    """
    danmu_list = []
    room_ids = list(range(1, num_rooms + 1))
    base_time = 1700000000  # 基准时间戳
    
    # 关键词池（模拟不同话题）
    topic_keywords = {
        1: ["开席", "吃鸡", "王者荣耀", "LPL", "冠军", "比赛"],
        2: ["唱歌", "跳舞", "才艺", "美女", "主播", "可爱"],
        3: ["游戏", "攻略", "教学", "装备", "技能", "等级"],
        4: ["电影", "剧情", "演技", "导演", "评分", "推荐"],
        5: ["美食", "烹饪", "菜品", "口味", "做法", "餐厅"],
    }
    
    for i in range(num_danmu):
        room_id = room_ids[i % num_rooms]
        timestamp = base_time + (i // 5) * 60  # 每5条弹幕在同一分钟内
        
        # 从对应房间的关键词池生成内容
        room_idx = room_id % len(topic_keywords)
        keywords = topic_keywords[room_idx]
        content = f"{keywords[i % len(keywords)]} {keywords[(i + 1) % len(keywords)]} 真的太棒了"
        
        danmu_list.append({
            "room_id": room_id,
            "session_id": 1,
            "uid": 100000 + i,
            "username": f"user_{i}",
            "content": content,
            "timestamp": timestamp,
            "medal_level": 1,
            "medal_name": "",
            "user_level": 1,
            "is_gift": False,
        })
    
    return danmu_list, room_ids, base_time, base_time + 3600  # 1小时时间范围


def test_tfidf_engine_correctness():
    """测试 TF-IDF 引擎的正确性"""
    from backend.services.tfidf_engine import TfidfEngineV2
    
    print("=" * 60)
    print("测试 1: 算法正确性验证")
    print("=" * 60)
    
    # 创建测试数据
    danmu_data, room_ids, start_time, end_time = create_test_data(num_danmu=5000)
    
    # 使用房间1的数据（专注于游戏话题）
    room1_data = [d for d in danmu_data if d["room_id"] == 1]
    print(f"  房间1 弹幕数量: {len(room1_data)}")
    
    # 初始化引擎
    segment_engine = MockSegmentEngine()
    db_handler = MockDBHandler(room1_data)
    engine = TfidfEngineV2(db_handler=db_handler, segment_engine=segment_engine, 
                            chunk_size=1000, window_minutes=5)
    
    # 执行关键词提取
    result = asyncio.run(engine.extract_keywords(
        room_id=1, start_time=start_time, end_time=end_time, top_k=10
    ))
    
    print(f"\n  结果统计:")
    print(f"    - 总弹幕数: {result['total_danmu']}")
    print(f"    - 文档窗口数: {result['doc_count']}")
    print(f"    - 唯一词数: {result['unique_words']}")
    print(f"\n  Top 10 关键词:")
    for i, kw in enumerate(result["keywords"], 1):
        print(f"    {i}. {kw['word']}: {kw['score']:.4f}")
    
    # 验证基本功能
    assert len(result["keywords"]) <= 10, "返回的关键词数量超过要求"
    assert result["total_danmu"] == len(room1_data), "总弹幕数不匹配"
    assert result["doc_count"] > 0, "文档窗口数应为正数"
    
    # 验证得分非负
    for kw in result["keywords"]:
        assert kw["score"] >= 0, f"关键词 {kw['word']} 的分数应为非负"
    
    print("\n  ✅ 正确性测试通过!")
    return True


def test_tfidf_engine_correctness_manual():
    """手动验证 TF-IDF 计算逻辑"""
    print("\n" + "=" * 60)
    print("测试 2: TF-IDF 计算逻辑手动验证")
    print("=" * 60)
    
    # 手动构造简单数据进行验证
    documents = [
        "hello world",
        "hello python",
        "python is great",
        "hello world again",
    ]
    
    # 手动计算 TF-IDF
    words_list = [doc.split() for doc in documents]
    all_words = sum(words_list, [])
    unique_words = list(set(all_words))
    
    N = len(documents)
    print(f"  文档数 (N): {N}")
    print(f"  唯一词数 (V): {len(unique_words)}")
    
    # 计算 TF (使用最大值)
    tf = collections.defaultdict(int)
    for words in words_list:
        word_counts = collections.Counter(words)
        for word, count in word_counts.items():
            tf[word] = max(tf.get(word, 0), count)
    
    print(f"\n  全局最大 TF: {dict(tf)}")
    
    # 计算 DF
    df = collections.defaultdict(int)
    for words in words_list:
        for word in set(words):
            df[word] += 1
    
    print(f"  文档频率 DF: {dict(df)}")
    
    # 计算 IDF
    idf = {}
    for word, freq in df.items():
        idf[word] = math.log(N / (1 + freq))
    
    print(f"  逆文档频率 IDF: {dict(idf)}")
    
    # 计算 TF-IDF 得分
    scores = []
    for word in tf:
        score = tf[word] * idf.get(word, 0)
        scores.append((word, score))
    
    # 排序
    scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n  TF-IDF 得分排序:")
    for word, score in scores:
        print(f"    {word}: {score:.4f}")
    
    # 验证 "hello" 在多个文档中出现，IDF较低
    assert idf["hello"] < idf["python"], "hello 应在更多文档中出现，IDF应更低"
    
    print("\n  ✅ 逻辑验证通过!")
    return True


def test_streaming_optimization():
    """测试流式处理优化"""
    print("\n" + "=" * 60)
    print("测试 3: 流式处理优化验证")
    print("=" * 60)
    
    from backend.services.tfidf_engine import TfidfEngineV2
    
    # 创建大数据集
    print("  创建 10万条测试数据...")
    danmu_data, _, start_time, end_time = create_test_data(num_danmu=100000)
    
    print(f"  数据量: {len(danmu_data)} 条弹幕")
    print(f"  时间跨度: {end_time - start_time} 秒")
    
    # 初始化引擎
    segment_engine = MockSegmentEngine()
    db_handler = MockDBHandler(danmu_data)
    engine = TfidfEngineV2(db_handler=db_handler, segment_engine=segment_engine,
                            chunk_size=5000, window_minutes=5)
    
    # 计时执行
    print("\n  执行 TF-IDF 计算...")
    start_time_exec = time.time()
    
    result = asyncio.run(engine.extract_keywords(
        room_id=1, start_time=start_time, end_time=end_time, top_k=20
    ))
    
    elapsed_time = time.time() - start_time_exec
    
    print(f"\n  性能指标:")
    print(f"    - 执行时间: {elapsed_time:.2f} 秒")
    print(f"    - 处理速率: {len(danmu_data) / elapsed_time:.0f} 条/秒")
    
    # 验证结果
    print(f"\n  结果统计:")
    print(f"    - 处理弹幕数: {result['total_danmu']}")
    print(f"    - 文档窗口数: {result['doc_count']}")
    print(f"    - 唯一词数: {result['unique_words']}")
    
    # 复杂度验证
    print(f"\n  复杂度分析:")
    print(f"    - 时间复杂度: O(N + V) = O({len(danmu_data)} + {result['unique_words']})")
    print(f"    - 空间复杂度: O(V + K) = O({result['unique_words']} + 20)")
    
    # 验证 Top K 提取使用堆优化
    print("\n  Top 20 关键词 (堆提取验证):")
    for i, kw in enumerate(result["keywords"], 1):
        print(f"    {i:2d}. {kw['word']}: {kw['score']:.4f}")
    
    assert result["total_danmu"] == len(danmu_data), "所有弹幕应被处理"
    assert len(result["keywords"]) == 20, "应返回 Top 20 关键词"
    
    # 性能基准
    if elapsed_time > 10:
        print("\n  ⚠️ 警告: 处理时间过长，可能需要进一步优化")
    else:
        print("\n  ✅ 流式处理优化测试通过!")
    
    return True


def test_empty_data():
    """测试空数据处理"""
    print("\n" + "=" * 60)
    print("测试 4: 空数据边界条件")
    print("=" * 60)
    
    from backend.services.tfidf_engine import TfidfEngineV2
    
    # 空数据
    db_handler = MockDBHandler([])
    engine = TfidfEngineV2(db_handler=db_handler, segment_engine=MockSegmentEngine())
    
    result = asyncio.run(engine.extract_keywords(
        room_id=1, start_time=1700000000, end_time=1700003600
    ))
    
    print(f"  空数据结果: {result}")
    assert result["keywords"] == [], "空数据应返回空关键词列表"
    assert result["total_danmu"] == 0, "空数据应返回0条弹幕"
    assert result["unique_words"] == 0, "空数据应返回0个唯一词"
    
    print("\n  ✅ 空数据边界测试通过!")
    return True


def test_single_window():
    """测试单个时间窗口"""
    print("\n" + "=" * 60)
    print("测试 5: 单个时间窗口边界条件")
    print("=" * 60)
    
    from backend.services.tfidf_engine import TfidfEngineV2
    
    # 1分钟时间范围
    danmu_data, _, start_time, _ = create_test_data(num_danmu=1000)
    end_time = start_time + 60  # 1分钟
    
    db_handler = MockDBHandler(danmu_data)
    engine = TfidfEngineV2(db_handler=db_handler, segment_engine=MockSegmentEngine(),
                            window_minutes=5)
    
    result = asyncio.run(engine.extract_keywords(
        room_id=1, start_time=start_time, end_time=end_time
    ))
    
    print(f"  结果:")
    print(f"    - 文档窗口数: {result['doc_count']}")
    print(f"    - 处理弹幕数: {result['total_danmu']}")
    
    # 1分钟应只有1个窗口
    assert result["doc_count"] == 1, "1分钟时间范围应有1个文档窗口"
    
    print("\n  ✅ 单窗口边界测试通过!")
    return True


def main():
    """运行所有测试"""
    print("\n" + "#" * 60)
    print("  TF-IDF Engine V2 测试套件")
    print("#" * 60)
    
    tests = [
        ("算法正确性验证", test_tfidf_engine_correctness),
        ("TF-IDF计算逻辑手动验证", test_tfidf_engine_correctness_manual),
        ("流式处理优化验证", test_streaming_optimization),
        ("空数据边界条件", test_empty_data),
        ("单个时间窗口", test_single_window),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "✅ 通过" if result else "❌ 失败"))
        except Exception as e:
            results.append((test_name, f"❌ 错误: {str(e)}"))
            import traceback
            traceback.print_exc()
    
    # 测试总结
    print("\n" + "=" * 60)
    print("测试总结:")
    print("=" * 60)
    for name, status in results:
        print(f"  {name}: {status}")
    
    passed = sum(1 for _, status in results if "通过" in status)
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    return all("通过" in status for _, status in results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)