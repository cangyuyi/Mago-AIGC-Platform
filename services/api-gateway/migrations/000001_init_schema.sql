-- +goose Up
-- Enable pgvector extension (for vector fields)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Note: pgvector extension can be installed via `CREATE EXTENSION vector;`
-- We use JSONB for embeddings in MVP, switch to pgvector in production if needed

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(512) NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(512),
    org_id UUID,
    role VARCHAR(32) NOT NULL DEFAULT 'owner',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_org ON users(org_id);

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Memberships
CREATE TABLE IF NOT EXISTS memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    org_id UUID NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'editor',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(user_id, org_id)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    aspect_ratio VARCHAR(16) NOT NULL DEFAULT '9:16',
    target_platform VARCHAR(64),
    target_duration INT,
    category VARCHAR(64),
    cover_image_url VARCHAR(512),
    owner_id UUID NOT NULL,
    org_id UUID,
    current_step VARCHAR(32),
    character_ids JSONB DEFAULT '[]',
    style_preset_ids JSONB DEFAULT '[]',
    reference_video_ids JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_org ON projects(org_id);
CREATE INDEX idx_projects_status ON projects(status);

-- Scripts
CREATE TABLE IF NOT EXISTS scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    title VARCHAR(512) NOT NULL,
    script_type VARCHAR(32) NOT NULL DEFAULT 'oral_sharing',
    duration_target INT,
    aspect_ratio VARCHAR(16) NOT NULL DEFAULT '9:16',
    target_platform VARCHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    hook TEXT,
    hook_type VARCHAR(64),
    body TEXT,
    cta TEXT,
    cta_type VARCHAR(64),
    tags JSONB DEFAULT '[]',
    emotion_arc JSONB DEFAULT '[]',
    quality_scores JSONB DEFAULT '{}',
    quality_feedback JSONB DEFAULT '[]',
    compliance_flags JSONB DEFAULT '[]',
    creative_brief JSONB DEFAULT '{}',
    model_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_scripts_project ON scripts(project_id);
CREATE INDEX idx_scripts_status ON scripts(status);

-- Storyboards
CREATE TABLE IF NOT EXISTS storyboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    title VARCHAR(255),
    total_duration FLOAT,
    shot_count INT,
    aspect_ratio VARCHAR(16) NOT NULL DEFAULT '9:16',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    model_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_storyboards_project ON storyboards(project_id);
CREATE INDEX idx_storyboards_script ON storyboards(script_id);

-- Storyboard Shots
CREATE TABLE IF NOT EXISTS storyboard_shots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storyboard_id UUID NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
    shot_index INT NOT NULL,
    duration FLOAT NOT NULL,
    shot_type VARCHAR(32),
    camera_movement VARCHAR(64),
    camera_angle VARCHAR(32),
    scene_environment TEXT NOT NULL,
    subject_description TEXT NOT NULL,
    props JSONB DEFAULT '[]',
    lighting TEXT,
    color_tone TEXT,
    composition TEXT,
    dialogue_narration TEXT,
    sound_effect TEXT,
    bgm_emotion VARCHAR(64),
    emotion_tag VARCHAR(32),
    transition_in VARCHAR(32),
    transition_out VARCHAR(32),
    motion_description TEXT,
    ai_generation_notes TEXT,
    consistency_hints JSONB DEFAULT '{}',
    quality_score INT,
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_shots_storyboard ON storyboard_shots(storyboard_id, shot_index);

-- Characters
CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID,
    org_id UUID,
    visibility VARCHAR(16) DEFAULT 'private',
    name VARCHAR(128) NOT NULL,
    description TEXT,
    gender VARCHAR(16),
    age_appearance VARCHAR(32),
    ethnicity VARCHAR(32),
    face_description TEXT,
    hair_description TEXT,
    body_description TEXT,
    clothing_default TEXT,
    skin_details TEXT,
    distinctive_features JSONB DEFAULT '[]',
    personality_vibe VARCHAR(128),
    faceid_weight FLOAT DEFAULT 0.8,
    ip_adapter_scale FLOAT DEFAULT 0.7,
    reference_strategy VARCHAR(32) DEFAULT 'faceid',
    seed_base INT,
    model_compatibility JSONB DEFAULT '{}',
    prompt_fragment TEXT NOT NULL,
    negative_fragment TEXT,
    tags JSONB DEFAULT '[]',
    is_preset BOOLEAN DEFAULT false,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_characters_owner ON characters(owner_id);

-- Style Presets
CREATE TABLE IF NOT EXISTS style_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID,
    org_id UUID,
    visibility VARCHAR(16) DEFAULT 'private',
    name VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL,
    description TEXT,
    positive_fragment TEXT NOT NULL,
    negative_fragment TEXT,
    dominant_colors JSONB DEFAULT '[]',
    lighting_style VARCHAR(64),
    color_tone VARCHAR(64),
    lens_and_camera VARCHAR(128),
    parameter_hints JSONB DEFAULT '{}',
    recommended_loras JSONB DEFAULT '[]',
    example_image_url VARCHAR(512),
    tags JSONB DEFAULT '[]',
    is_preset BOOLEAN DEFAULT false,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_styles_owner ON style_presets(owner_id);
CREATE INDEX idx_styles_category ON style_presets(category);

-- Trend Topics
CREATE TABLE IF NOT EXISTS trend_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    topic_id VARCHAR(255),
    title VARCHAR(512) NOT NULL,
    category VARCHAR(64),
    hot_value BIGINT,
    hot_value_growth FLOAT,
    rank_position INT,
    cover_url VARCHAR(512),
    url TEXT,
    tags JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'rising',
    lifecycle_stage VARCHAR(32),
    related_videos_count INT DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_trends_platform ON trend_topics(platform);
CREATE INDEX idx_trends_status ON trend_topics(status);
CREATE INDEX idx_trends_updated ON trend_topics(last_updated_at);

-- Viral Videos
CREATE TABLE IF NOT EXISTS viral_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    video_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    author_name VARCHAR(255),
    title VARCHAR(512),
    description TEXT,
    tags JSONB DEFAULT '[]',
    category VARCHAR(64),
    duration FLOAT,
    width INT,
    height INT,
    aspect_ratio VARCHAR(16),
    metrics JSONB DEFAULT '{}',
    viral_score FLOAT,
    analysis_status VARCHAR(20) DEFAULT 'pending',
    analysis_error TEXT,
    thumbnail_url VARCHAR(512),
    bgm_name VARCHAR(255),
    bgm_bpm FLOAT,
    bgm_emotion VARCHAR(64),
    analysis JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(platform, video_id)
);
CREATE INDEX idx_viral_platform ON viral_videos(platform);
CREATE INDEX idx_viral_category ON viral_videos(category);
CREATE INDEX idx_viral_status ON viral_videos(analysis_status);

-- Creative Sessions
CREATE TABLE IF NOT EXISTS creative_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_type VARCHAR(32) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    ideas JSONB DEFAULT '[]',
    selected_idea_id VARCHAR(64),
    debate_log JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_creative_project ON creative_sessions(project_id);

-- +goose Down
DROP TABLE IF EXISTS creative_sessions CASCADE;
DROP TABLE IF EXISTS viral_videos CASCADE;
DROP TABLE IF EXISTS trend_topics CASCADE;
DROP TABLE IF EXISTS style_presets CASCADE;
DROP TABLE IF EXISTS characters CASCADE;
DROP TABLE IF EXISTS storyboard_shots CASCADE;
DROP TABLE IF EXISTS storyboards CASCADE;
DROP TABLE IF EXISTS scripts CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS memberships CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS users CASCADE;
