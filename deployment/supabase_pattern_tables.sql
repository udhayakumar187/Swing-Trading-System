-- Pattern Tracking Tables for Supabase
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tracked Patterns Table
CREATE TABLE IF NOT EXISTS tracked_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    
    detection_timestamp TIMESTAMPTZ NOT NULL,
    detection_price DECIMAL(20, 4) NOT NULL,
    detection_volume DECIMAL(20, 2) DEFAULT 0,
    
    pattern_start_date DATE NOT NULL,
    pattern_end_date DATE NOT NULL,
    pattern_bars INTEGER NOT NULL,
    
    key_levels JSONB DEFAULT '{}',
    stop_loss DECIMAL(20, 4),
    target_price DECIMAL(20, 4),
    risk_reward_ratio DECIMAL(10, 2),
    
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
    volume_confirmation BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    
    outcome VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    outcome_timestamp TIMESTAMPTZ,
    outcome_price DECIMAL(20, 4),
    max_favorable_move DECIMAL(10, 4),
    max_adverse_move DECIMAL(10, 4),
    days_to_outcome INTEGER,
    
    forward_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for tracked_patterns
CREATE INDEX IF NOT EXISTS idx_tracked_patterns_symbol ON tracked_patterns(symbol);
CREATE INDEX IF NOT EXISTS idx_tracked_patterns_pattern_type ON tracked_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_tracked_patterns_outcome ON tracked_patterns(outcome);
CREATE INDEX IF NOT EXISTS idx_tracked_patterns_detection_ts ON tracked_patterns(detection_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tracked_patterns_symbol_type ON tracked_patterns(symbol, pattern_type);

-- Pattern Forward Tracking Table
CREATE TABLE IF NOT EXISTS pattern_forward_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tracked_pattern_id UUID NOT NULL REFERENCES tracked_patterns(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    
    tracking_start_date DATE NOT NULL,
    tracking_end_date DATE NOT NULL,
    tracking_days INTEGER NOT NULL,
    
    daily_data JSONB DEFAULT '[]',
    
    max_high DECIMAL(20, 4),
    max_high_date DATE,
    min_low DECIMAL(20, 4),
    min_low_date DATE,
    
    first_target_hit_date DATE,
    first_stop_hit_date DATE,
    
    price_at_1d DECIMAL(20, 4),
    price_at_3d DECIMAL(20, 4),
    price_at_5d DECIMAL(20, 4),
    price_at_10d DECIMAL(20, 4),
    price_at_20d DECIMAL(20, 4),
    
    return_1d DECIMAL(10, 4),
    return_3d DECIMAL(10, 4),
    return_5d DECIMAL(10, 4),
    return_10d DECIMAL(10, 4),
    return_20d DECIMAL(10, 4),
    
    max_drawdown DECIMAL(10, 4),
    max_runup DECIMAL(10, 4),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for pattern_forward_tracking
CREATE INDEX IF NOT EXISTS idx_forward_tracking_pattern ON pattern_forward_tracking(tracked_pattern_id);
CREATE INDEX IF NOT EXISTS idx_forward_tracking_symbol ON pattern_forward_tracking(symbol);

-- Pattern Scan Configuration Table
CREATE TABLE IF NOT EXISTS pattern_scan_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    symbols TEXT[] NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    lookback_days INTEGER NOT NULL DEFAULT 200,
    forward_days INTEGER NOT NULL DEFAULT 20,
    patterns_to_track TEXT[] NOT NULL,
    min_quality_score INTEGER NOT NULL DEFAULT 60,
    require_volume_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default configuration
INSERT INTO pattern_scan_config (name, symbols, timeframe, lookback_days, forward_days, patterns_to_track, min_quality_score, require_volume_confirmation)
VALUES (
    'default',
    ARRAY['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'],
    '1d',
    200,
    20,
    ARRAY[
        'BREAKOUT_VOLUME',
        'BREAKOUT_RETEST',
        'TREND_PULLBACK',
        'EMA_PULLBACK',
        'DOUBLE_BOTTOM',
        'DOUBLE_TOP',
        'BULL_FLAG',
        'BEAR_FLAG',
        'ASCENDING_TRIANGLE_BREAKOUT',
        'DESCENDING_TRIANGLE_BREAKDOWN',
        'SUPPORT_BOUNCE',
        'RESISTANCE_REJECTION'
    ],
    60,
    TRUE
)
ON CONFLICT (name) DO NOTHING;

-- Pattern Statistics View
CREATE OR REPLACE VIEW pattern_statistics AS
SELECT 
    pattern_type,
    symbol,
    COUNT(*) as total_detections,
    COUNT(*) FILTER (WHERE outcome = 'TARGET_HIT') as successful,
    COUNT(*) FILTER (WHERE outcome IN ('STOP_HIT', 'INVALIDATED')) as failed,
    COUNT(*) FILTER (WHERE outcome = 'PENDING') as pending,
    ROUND(
        COUNT(*) FILTER (WHERE outcome = 'TARGET_HIT')::NUMERIC / 
        NULLIF(COUNT(*), 0) * 100, 2
    ) as win_rate,
    ROUND(
        AVG(
            CASE 
                WHEN outcome IN ('TARGET_HIT', 'STOP_HIT', 'PARTIAL') AND detection_price > 0 
                THEN (outcome_price - detection_price) / detection_price * 
                     CASE WHEN direction = 'BEARISH' THEN -1 ELSE 1 END
            END
        ) * 100, 2
    ) as avg_return_pct,
    ROUND(
        AVG(
            CASE 
                WHEN outcome IN ('TARGET_HIT', 'STOP_HIT', 'PARTIAL') AND stop_loss IS NOT NULL AND detection_price > 0
                THEN ABS(outcome_price - detection_price) / ABS(detection_price - stop_loss)
            END
        ), 2
    ) as avg_r_multiple,
    ROUND(
        AVG(days_to_outcome)::NUMERIC, 1
    ) as avg_days_to_outcome
FROM tracked_patterns
GROUP BY pattern_type, symbol
ORDER BY total_detections DESC;

-- Pattern Performance Summary View
CREATE OR REPLACE VIEW pattern_performance_summary AS
SELECT 
    pattern_type,
    COUNT(*) as total_patterns,
    COUNT(*) FILTER (WHERE outcome = 'TARGET_HIT') as wins,
    COUNT(*) FILTER (WHERE outcome IN ('STOP_HIT', 'INVALIDATED')) as losses,
    COUNT(*) FILTER (WHERE outcome = 'PENDING') as pending,
    ROUND(
        COUNT(*) FILTER (WHERE outcome = 'TARGET_HIT')::NUMERIC / 
        NULLIF(COUNT(*), 0) * 100, 2
    ) as overall_win_rate,
    ROUND(
        AVG(
            CASE 
                WHEN outcome IN ('TARGET_HIT', 'STOP_HIT', 'PARTIAL') AND detection_price > 0 
                THEN (outcome_price - detection_price) / detection_price * 
                     CASE WHEN direction = 'BEARISH' THEN -1 ELSE 1 END
            END
        ) * 100, 2
    ) as avg_return_pct,
    ROUND(
        AVG(
            CASE 
                WHEN outcome IN ('TARGET_HIT', 'STOP_HIT', 'PARTIAL') AND stop_loss IS NOT NULL AND detection_price > 0
                THEN ABS(outcome_price - detection_price) / ABS(detection_price - stop_loss)
            END
        ), 2
    ) as avg_r_multiple,
    MAX(max_favorable_move) * 100 as best_move_pct,
    MAX(max_adverse_move) * 100 as worst_move_pct
FROM tracked_patterns
GROUP BY pattern_type
ORDER BY total_patterns DESC;

-- Row Level Security (optional - enable if needed)
-- ALTER TABLE tracked_patterns ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pattern_forward_tracking ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pattern_scan_config ENABLE ROW LEVEL SECURITY;

-- Grant permissions (adjust as needed for your Supabase setup)
-- GRANT ALL ON tracked_patterns TO authenticated;
-- GRANT ALL ON pattern_forward_tracking TO authenticated;
-- GRANT ALL ON pattern_scan_config TO authenticated;
-- GRANT ALL ON pattern_statistics TO authenticated;
-- GRANT ALL ON pattern_performance_summary TO authenticated;