#!/usr/bin/env python3
"""
测试项目导入和基础功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试关键模块导入"""
    print("测试模块导入...")

    try:
        # 测试数据收集器模块
        from src.data_collection.base_collector import DataCollector, DataSourceType
        print("✓ 数据收集器模块导入成功")

        from src.data_collection.manager import DataCollectionManager
        print("✓ 数据收集管理器导入成功")

        # 测试API模块
        from src.api.config import settings
        print("✓ API配置模块导入成功")

        from src.api.models.response import SuccessResponse, ErrorResponse
        print("✓ API响应模型导入成功")

        # 测试FastAPI
        import fastapi
        print("✓ FastAPI导入成功")

        # 测试数据库驱动
        import asyncpg
        print("✓ asyncpg导入成功")

        # 测试数据处理库
        import polars
        print("✓ polars导入成功")

        return True

    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 导入错误: {e}")
        return False

def test_config():
    """测试配置加载"""
    print("\n测试配置加载...")

    try:
        from src.api.config import settings

        print(f"应用名称: {settings.APP_NAME}")
        print(f"环境: {settings.ENVIRONMENT}")
        print(f"调试模式: {settings.DEBUG}")
        print(f"数据库URL: {settings.DATABASE_URL}")

        return True

    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False

def test_docker_compose():
    """检查Docker Compose文件"""
    print("\n检查Docker Compose配置...")

    try:
        import yaml

        with open('docker-compose.yml', 'r') as f:
            docker_compose = yaml.safe_load(f)

        services = docker_compose.get('services', {})
        print(f"找到 {len(services)} 个服务:")

        for service_name in services:
            print(f"  - {service_name}")

        # 检查关键服务
        required_services = ['postgres', 'redis', 'minio', 'api']
        missing_services = [s for s in required_services if s not in services]

        if missing_services:
            print(f"✗ 缺少服务: {missing_services}")
            return False
        else:
            print("✓ 所有关键服务都存在")
            return True

    except Exception as e:
        print(f"✗ Docker Compose检查失败: {e}")
        return False

def test_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")

    required_dirs = [
        'src/data_collection',
        'src/data_processing',
        'src/ai_analysis',
        'src/prediction',
        'src/workflow',
        'src/api',
        'src/storage',
        'src/web/frontend',
        'tests',
        'docs',
        'scripts',
        'config'
    ]

    missing_dirs = []

    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
        else:
            print(f"✓ 目录存在: {dir_path}")

    if missing_dirs:
        print(f"✗ 缺少目录: {missing_dirs}")
        return False
    else:
        print("✓ 所有目录都存在")
        return True

def test_requirements():
    """检查依赖文件"""
    print("\n检查依赖文件...")

    required_files = [
        'requirements.txt',
        'package.json',
        '.env.example',
        'docker-compose.yml',
        'Makefile',
        'README.md'
    ]

    missing_files = []

    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✓ 文件存在: {file_path}")

    if missing_files:
        print(f"✗ 缺少文件: {missing_files}")
        return False
    else:
        print("✓ 所有文件都存在")
        return True

def main():
    """主测试函数"""
    print("=" * 60)
    print("地缘政治分析AI工作流系统 - 项目结构测试")
    print("=" * 60)

    tests = [
        test_project_structure,
        test_requirements,
        test_docker_compose,
        test_imports,
        test_config
    ]

    results = []

    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"测试 {test_func.__name__} 出错: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    for i, (test_func, result) in enumerate(zip(tests, results), 1):
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{i}. {test_func.__name__}: {status}")

    total_passed = sum(results)
    total_tests = len(results)

    print(f"\n总计: {total_passed}/{total_tests} 个测试通过")

    if total_passed == total_tests:
        print("\n🎉 所有测试通过！项目结构完整。")
        print("\n下一步:")
        print("1. 复制 .env.example 到 .env 并配置环境变量")
        print("2. 运行 'docker-compose up -d' 启动服务")
        print("3. 运行 'make install-dev' 安装Python依赖")
        print("4. 访问 http://localhost:8000/docs 查看API文档")
        return 0
    else:
        print("\n⚠️ 有些测试失败，请检查项目结构。")
        return 1

if __name__ == "__main__":
    sys.exit(main())