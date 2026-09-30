-- +goose Up

-- Migration 002: Trend Intelligence Module
-- Adds: video_shots, viral_patterns, crawl_tasks tables + enhances viral_videos/trend_topics

-- Add missing columns to trend_topics
ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS hot_value_history JSONB DEFAULT '[]';
ALTER TABLE trend_topics ADD COLUMN IF NOT EXISTS related_video_ids JSONB DEFAULT '[]';
CREATE INDEX IF NOT EXISTS idx_trends_lifecycle ON trend_topics(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_trends_hot_growth ON trend_topics(hot_value_growth DESC);

-- Add embedding and content columns to viral_videos
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS embedding JSONB DEFAULT '[]';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS transcript TEXT;
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS asr_language VARCHAR(16);
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS shot_count INT DEFAULT 0;
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS avg_shot_duration FLOAT;
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS hook_text TEXT;
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS hook_type VARCHAR(64);
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS hook_engagement_score FLOAT;
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS narrative_structure JSONB DEFAULT '{}';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS visual_language JSONB DEFAULT '{}';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS rhythm_analysis JSONB DEFAULT '{}';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS emotion_curve JSONB DEFAULT '[]';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS keyframe_urls JSONB DEFAULT '[]';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS pattern_ids JSONB DEFAULT '[]';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS analysis_version VARCHAR(32) DEFAULT 'v1';
ALTER TABLE viral_videos ADD COLUMN IF NOT EXISTS extra_metadata JSONB DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_viral_score ON viral_videos(viral_score DESC);
CREATE INDEX IF NOT EXISTS idx_viral_analyzed ON viral_videos(analyzed_at DESC);

-- Video Shots table (individual shot-level analysis for each viral video)
CREATE TABLE IF NOT EXISTS video_shots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    viral_video_id UUID NOT NULL REFERENCES viral_videos(id) ON DELETE CASCADE,
    shot_index INT NOT NULL,
    start_time FLOAT NOT NULL,           -- seconds
    end_time FLOAT NOT NULL,             -- seconds
    duration FLOAT NOT NULL,
    keyframe_url VARCHAR(512),
    keyframe_path VARCHAR(512),          -- local path for processing
    transcript TEXT,                      -- ASR text for this shot
    transcript_words JSONB DEFAULT '[]',  -- word-level timing [{word,start,end,confidence}]
    visual_description TEXT,              -- multimodal LLM description
    visual_tags JSONB DEFAULT '[]',
    camera_movement VARCHAR(64),
    camera_angle VARCHAR(32),
    lighting VARCHAR(64),
    color_palette JSONB DEFAULT '[]',
    emotion_tag VARCHAR(32),
    text_ocr TEXT,                        -- on-screen text detected
    transition_type VARCHAR(32),          -- cut/dissolve/wipe/etc
    has_face BOOLEAN DEFAULT false,
    face_count INT DEFAULT 0,
    motion_intensity FLOAT DEFAULT 0,     -- 0-1, amount of visual motion
    audio_type VARCHAR(32),               -- speech/music/silence/effect
    onset_strength FLOAT DEFAULT 0,       -- audio onset at start
    objects_detected JSONB DEFAULT '[]',
    quality_score FLOAT DEFAULT 0,        -- visual quality 0-1
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_shots_video ON video_shots(viral_video_id, shot_index);
CREATE INDEX IF NOT EXISTS idx_shots_emotion ON video_shots(emotion_tag);

-- Viral Patterns table (extracted high-performing formulas/patterns)
CREATE TABLE IF NOT EXISTS viral_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(64) NOT NULL,    -- hook/narrative/editing/audio/visual/structure
    category VARCHAR(64),                 -- 美妆/美食/3C/剧情/知识/...
    description TEXT NOT NULL,
    formula_template TEXT,                -- reusable template text
    avg_viral_score FLOAT DEFAULT 0,
    sample_count INT DEFAULT 0,           -- how many videos matched this pattern
    example_video_ids JSONB DEFAULT '[]',
    trigger_conditions JSONB DEFAULT '{}', -- when this pattern works best
    applicable_platforms JSONB DEFAULT '[]',
    applicable_duration_range JSONB DEFAULT '{}', -- {min_sec, max_sec}
    key_visuals JSONB DEFAULT '[]',
    key_phrases JSONB DEFAULT '[]',       -- common hook phrases
    audio_characteristics JSONB DEFAULT '{}',
    editing_characteristics JSONB DEFAULT '{}',
    success_rate FLOAT DEFAULT 0,         -- 0-1, videos with pattern that performed well
    embedding JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    is_verified BOOLEAN DEFAULT false,    -- human-verified pattern
    source VARCHAR(32) DEFAULT 'ai_extracted', -- ai_extracted/manual/imported
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON viral_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_category ON viral_patterns(category);
CREATE INDEX IF NOT EXISTS idx_patterns_score ON viral_patterns(avg_viral_score DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_verified ON viral_patterns(is_verified);

-- Crawl Tasks table (tracking crawl job execution)
CREATE TABLE IF NOT EXISTS crawl_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    task_type VARCHAR(32) NOT NULL,       -- hot_list/video_detail/user_profile/search
    status VARCHAR(20) DEFAULT 'pending', -- pending/running/success/failed/partial
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    items_found INT DEFAULT 0,
    items_new INT DEFAULT 0,
    items_updated INT DEFAULT 0,
    items_failed INT DEFAULT 0,
    error_message TEXT,
    proxy_used VARCHAR(128),
    crawl_params JSONB DEFAULT '{}',
    duration_ms INT DEFAULT 0,
    triggered_by VARCHAR(32) DEFAULT 'scheduler', -- scheduler/manual/api
    worker_id VARCHAR(64),
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crawl_platform ON crawl_tasks(platform);
CREATE INDEX IF NOT EXISTS idx_crawl_status ON crawl_tasks(status);
CREATE INDEX IF NOT EXISTS idx_crawl_type ON crawl_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_crawl_created ON crawl_tasks(created_at DESC);

-- Topic Recommendations cache (generated topic cards)
CREATE TABLE IF NOT EXISTS topic_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    org_id UUID,
    category VARCHAR(64),
    keywords JSONB DEFAULT '[]',
    reference_video_urls JSONB DEFAULT '[]',
    topics JSONB NOT NULL DEFAULT '[]',      -- array of topic cards
    model_info JSONB DEFAULT '{}',
    feedback JSONB DEFAULT '{}',             -- user feedback (likes/dislikes)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_topic_rec_user ON topic_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_topic_rec_created ON topic_recommendations(created_at DESC);
