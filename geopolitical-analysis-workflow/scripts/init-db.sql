-- 地缘政治分析系统数据库初始化脚本
-- PostgreSQL + TimescaleDB

-- 启用TimescaleDB扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 创建枚举类型
CREATE TYPE data_source_type AS ENUM (
    'news',
    'financial',
    'social_media',
    'ads_b',
    'ais',
    'military',
    'osint',
    'weather',
    'satellite',
    'other'
);

CREATE TYPE data_format_type AS ENUM (
    'json',
    'xml',
    'csv',
    'text',
    'binary',
    'html'
);

CREATE TYPE processing_status_type AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'archived'
);

CREATE TYPE prediction_confidence_type AS ENUM (
    'low',
    'medium',
    'high'
);

-- 用户和认证表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    client_id VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);

-- 数据源配置表
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    type data_source_type NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1,
    collection_interval INTEGER DEFAULT 3600, -- 秒
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 原始数据表（TimescaleDB超级表）
CREATE TABLE raw_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES data_sources(id),
    source_type data_source_type NOT NULL,
    external_id VARCHAR(255),
    raw_data JSONB NOT NULL,
    data_format data_format_type DEFAULT 'json',
    metadata JSONB DEFAULT '{}',
    collected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ,
    processing_status processing_status_type DEFAULT 'pending',
    errors TEXT[] DEFAULT '{}',
    CONSTRAINT raw_data_external_id_unique UNIQUE(source_type, external_id)
);

-- 转换为TimescaleDB超级表
SELECT create_hypertable('raw_data', 'collected_at');

-- 为常用查询创建索引
CREATE INDEX idx_raw_data_source_type ON raw_data(source_type);
CREATE INDEX idx_raw_data_processing_status ON raw_data(processing_status);
CREATE INDEX idx_raw_data_collected_at_desc ON raw_data(collected_at DESC);

-- 处理后的数据表
CREATE TABLE processed_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data_id UUID REFERENCES raw_data(id),
    source_type data_source_type NOT NULL,
    data_type VARCHAR(255) NOT NULL,
    processed_data JSONB NOT NULL,
    features JSONB DEFAULT '{}',
    quality_score FLOAT DEFAULT 1.0,
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- 地理事件表
CREATE TABLE geo_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    location GEOGRAPHY(POINT, 4326),
    region VARCHAR(255),
    country VARCHAR(255),
    severity INTEGER CHECK (severity >= 1 AND severity <= 10),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    sources UUID[] DEFAULT '{}', -- 引用raw_data.id
    confidence FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 为地理查询创建索引
CREATE INDEX idx_geo_events_location ON geo_events USING GIST(location);
CREATE INDEX idx_geo_events_region ON geo_events(region);
CREATE INDEX idx_geo_events_start_time ON geo_events(start_time DESC);

-- 金融数据表（TimescaleDB超级表）
CREATE TABLE financial_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(50) NOT NULL,
    data_type VARCHAR(50) NOT NULL, -- 'stock', 'currency', 'commodity', 'index'
    open_price DECIMAL(20, 6),
    high_price DECIMAL(20, 6),
    low_price DECIMAL(20, 6),
    close_price DECIMAL(20, 6),
    volume BIGINT,
    market_cap DECIMAL(30, 2),
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- 转换为TimescaleDB超级表
SELECT create_hypertable('financial_data', 'timestamp');

-- 为金融数据创建索引
CREATE INDEX idx_financial_data_symbol ON financial_data(symbol);
CREATE INDEX idx_financial_data_timestamp_desc ON financial_data(timestamp DESC);
CREATE INDEX idx_financial_data_symbol_timestamp ON financial_data(symbol, timestamp DESC);

-- 预测模型表
CREATE TABLE prediction_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    model_type VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    parameters JSONB DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    trained_at TIMESTAMPTZ,
    file_path VARCHAR(500)
);

-- 预测结果表（TimescaleDB超级表）
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES prediction_models(id),
    target_type VARCHAR(255) NOT NULL, -- 'geopolitical_event', 'market_trend', 'risk_level'
    target_id VARCHAR(255), -- 具体目标标识
    predicted_value JSONB NOT NULL,
    confidence prediction_confidence_type DEFAULT 'medium',
    confidence_score FLOAT DEFAULT 0.5,
    prediction_horizon INTEGER, -- 预测范围（天）
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- 转换为TimescaleDB超级表
SELECT create_hypertable('predictions', 'generated_at');

-- 回测结果表
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(255) NOT NULL,
    model_id UUID REFERENCES prediction_models(id),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    initial_capital DECIMAL(20, 2),
    final_capital DECIMAL(20, 2),
    total_return DECIMAL(10, 4),
    annualized_return DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(10, 4),
    trades_count INTEGER,
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 工作流执行表
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    status processing_status_type DEFAULT 'pending',
    input_data JSONB DEFAULT '{}',
    output_data JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    errors TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 系统监控表（TimescaleDB超级表）
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 转换为TimescaleDB超级表
SELECT create_hypertable('system_metrics', 'timestamp');

-- 创建视图
CREATE VIEW data_collection_stats AS
SELECT
    source_type,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE processing_status = 'completed') as completed,
    COUNT(*) FILTER (WHERE processing_status = 'failed') as failed,
    COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
    MIN(collected_at) as first_collection,
    MAX(collected_at) as last_collection
FROM raw_data
GROUP BY source_type;

CREATE VIEW daily_prediction_summary AS
SELECT
    DATE(generated_at) as date,
    target_type,
    COUNT(*) as prediction_count,
    AVG(confidence_score) as avg_confidence,
    MIN(confidence_score) as min_confidence,
    MAX(confidence_score) as max_confidence
FROM predictions
GROUP BY DATE(generated_at), target_type;

-- 创建函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_geo_events_updated_at BEFORE UPDATE ON geo_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建数据保留策略（自动删除90天前的原始数据）
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    DELETE FROM raw_data
    WHERE collected_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
END;
$$ language 'plpgsql';

-- 插入初始数据
INSERT INTO users (username, email, password_hash, full_name, is_admin)
VALUES
    ('admin', 'admin@geopolitical.ai', -- 密码需要加密
     '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- 默认密码: admin123
     '系统管理员', true),
    ('analyst', 'analyst@geopolitical.ai',
     '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
     '数据分析师', false);

-- 插入默认数据源配置
INSERT INTO data_sources (name, type, description, config, is_enabled, priority)
VALUES
    ('news_api', 'news', '新闻数据源',
     '{"api_key": "YOUR_NEWS_API_KEY", "sources": ["bbc-news", "cnn", "reuters"], "languages": ["en"]}',
     true, 1),
    ('financial_data', 'financial', '金融数据源',
     '{"provider": "alpha_vantage", "api_key": "YOUR_ALPHA_VANTAGE_KEY", "symbols": ["AAPL", "MSFT", "GOOGL"]}',
     true, 1),
    ('ads_b_tracker', 'ads_b', '航空数据追踪',
     '{"api_url": "https://opensky-network.org/api", "regions": ["global"], "max_altitude": 10000}',
     true, 2),
    ('ais_tracker', 'ais', '船舶数据追踪',
     '{"api_url": "https://services.marinetraffic.com/api", "api_key": "YOUR_AIS_KEY", "areas": ["global"]}',
     true, 2),
    ('twitter_osint', 'osint', 'Twitter OSINT数据',
     '{"api_key": "YOUR_TWITTER_KEY", "keywords": ["geopolitics", "conflict", "military"], "languages": ["en"]}',
     false, 3); -- 默认禁用，需要配置API密钥

-- 插入默认预测模型
INSERT INTO prediction_models (name, model_type, description, version, is_active)
VALUES
    ('geopolitical_risk_v1', 'ensemble', '地缘政治风险预测模型', '1.0.0', true),
    ('market_trend_v1', 'time_series', '市场趋势预测模型', '1.0.0', true),
    ('event_detection_v1', 'nlp', '事件检测模型', '1.0.0', true);

-- 输出初始化完成信息
SELECT '数据库初始化完成！' as message;