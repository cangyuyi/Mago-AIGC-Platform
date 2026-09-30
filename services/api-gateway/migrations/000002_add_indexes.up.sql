-- +goose Up

-- Performance indexes for Mago Agent Platform.
-- Keep this migration aligned with the canonical table/column names in 000001+.

CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_owner_updated ON projects(owner_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_scripts_project_id ON scripts(project_id);
CREATE INDEX IF NOT EXISTS idx_scripts_created_at ON scripts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scripts_project_created ON scripts(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_storyboards_script_id ON storyboards(script_id);
CREATE INDEX IF NOT EXISTS idx_storyboards_created_at ON storyboards(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_characters_owner_id ON characters(owner_id);
CREATE INDEX IF NOT EXISTS idx_characters_created_at ON characters(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_style_presets_category ON style_presets(category);
CREATE INDEX IF NOT EXISTS idx_style_presets_created_at ON style_presets(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trend_topics_platform ON trend_topics(platform);
CREATE INDEX IF NOT EXISTS idx_trend_topics_created_at ON trend_topics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_topics_rank ON trend_topics(rank_position);

CREATE INDEX IF NOT EXISTS idx_viral_videos_platform ON viral_videos(platform);
CREATE INDEX IF NOT EXISTS idx_viral_videos_created_at ON viral_videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_viral_videos_score ON viral_videos(viral_score DESC);

