-- +goose Down

DROP INDEX IF EXISTS idx_users_created_at;
DROP INDEX IF EXISTS idx_projects_created_at;
DROP INDEX IF EXISTS idx_projects_owner_updated;
DROP INDEX IF EXISTS idx_scripts_project_id;
DROP INDEX IF EXISTS idx_scripts_created_at;
DROP INDEX IF EXISTS idx_scripts_project_created;
DROP INDEX IF EXISTS idx_storyboards_script_id;
DROP INDEX IF EXISTS idx_storyboards_created_at;
DROP INDEX IF EXISTS idx_characters_owner_id;
DROP INDEX IF EXISTS idx_characters_created_at;
DROP INDEX IF EXISTS idx_style_presets_category;
DROP INDEX IF EXISTS idx_style_presets_created_at;
DROP INDEX IF EXISTS idx_trend_topics_platform;
DROP INDEX IF EXISTS idx_trend_topics_created_at;
DROP INDEX IF EXISTS idx_trend_topics_rank;
DROP INDEX IF EXISTS idx_viral_videos_platform;
DROP INDEX IF EXISTS idx_viral_videos_created_at;
DROP INDEX IF EXISTS idx_viral_videos_score;
