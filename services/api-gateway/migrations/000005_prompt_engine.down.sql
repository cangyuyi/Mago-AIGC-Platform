-- +goose Down

DROP INDEX IF EXISTS idx_prompt_pkg_created_at;
DROP TABLE IF EXISTS model_configs CASCADE;
DROP TABLE IF EXISTS prompts CASCADE;
DROP TABLE IF EXISTS prompt_packages CASCADE;
