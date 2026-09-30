-- +goose Down

-- Rollback: Drop tables first (due to FK), then columns
DROP TABLE IF EXISTS topic_recommendations CASCADE;
DROP TABLE IF EXISTS crawl_tasks CASCADE;
DROP TABLE IF EXISTS viral_patterns CASCADE;
DROP TABLE IF EXISTS video_shots CASCADE;

ALTER TABLE viral_videos DROP COLUMN IF EXISTS embedding;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS transcript;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS asr_language;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS shot_count;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS avg_shot_duration;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS hook_text;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS hook_type;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS hook_engagement_score;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS narrative_structure;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS visual_language;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS rhythm_analysis;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS emotion_curve;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS keyframe_urls;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS pattern_ids;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS analyzed_at;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS analysis_version;
ALTER TABLE viral_videos DROP COLUMN IF EXISTS extra_metadata;

ALTER TABLE trend_topics DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE trend_topics DROP COLUMN IF EXISTS updated_at;
ALTER TABLE trend_topics DROP COLUMN IF EXISTS hot_value_history;
ALTER TABLE trend_topics DROP COLUMN IF EXISTS related_video_ids;
