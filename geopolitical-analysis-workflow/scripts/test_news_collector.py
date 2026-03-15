#!/usr/bin/env python3
"""
测试新闻收集器
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_news_collector():
    """测试新闻收集器"""
    print("测试新闻收集器...")

    try:
        from src.data_collection.base_collector import CollectorConfig, DataSourceType
        from src.data_collection.collectors.news_collector import NewsCollector

        # 创建配置
        config = CollectorConfig(
            name="test_news_collector",
            source_type=DataSourceType.NEWS,
            interval_seconds=3600,
            batch_size=10,
            params={
                "sources": [
                    {
                        "type": "rss",
                        "name": "reuters_test",
                        "config": {
                            "feed_url": "http://feeds.reuters.com/Reuters/worldNews"
                        }
                    }
                ]
            }
        )

        # 创建收集器实例
        collector = NewsCollector(config)
        print(f"✓ 新闻收集器创建成功: {collector.name}")

        # 测试连接（可能失败，因为需要网络）
        print("测试连接...")
        connection_ok = await collector.test_connection()
        print(f"连接测试结果: {connection_ok}")

        # 尝试收集少量数据
        print("尝试收集数据（最多5条）...")
        records = await collector.collect()
        print(f"收集到 {len(records)} 条记录")

        for i, record in enumerate(records[:3]):
            print(f"记录 {i+1}: {record.id}")
            print(f"  标题: {record.raw_data.get('title', '无标题')}")
            print(f"  来源: {record.raw_data.get('source', '未知')}")
            print()

        if records:
            # 验证记录
            valid_count = sum(1 for record in records if collector.validate(record))
            print(f"有效记录: {valid_count}/{len(records)}")

        print("✓ 新闻收集器测试完成")
        return True

    except ImportError as e:
        print(f"✗ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_manager():
    """测试数据收集管理器"""
    print("\n测试数据收集管理器...")

    try:
        from src.data_collection.manager import get_manager

        # 获取管理器实例（使用配置文件）
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "config", "collectors.yaml")
        manager = await get_manager(config_path)

        print(f"✓ 数据收集管理器创建成功")
        print(f"收集器状态: {manager.get_status()}")

        # 测试立即收集
        print("测试立即收集...")
        results = await manager.collect_now(["news_collector"])
        print(f"收集结果: {list(results.keys())}")

        for name, records in results.items():
            print(f"  {name}: {len(records)} 条记录")

        print("✓ 数据收集管理器测试完成")
        return True

    except Exception as e:
        print(f"✗ 管理器测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("=" * 60)
    print("新闻收集器测试")
    print("=" * 60)

    # 设置环境变量（如果需要）
    if not os.getenv("NEWS_API_KEY"):
        print("注意: NEWS_API_KEY 环境变量未设置，NewsAPI源将不可用")

    # 运行测试
    test1_ok = await test_news_collector()
    test2_ok = await test_manager()

    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"新闻收集器测试: {'通过' if test1_ok else '失败'}")
    print(f"数据收集管理器测试: {'通过' if test2_ok else '失败'}")
    print("=" * 60)

    return test1_ok and test2_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)