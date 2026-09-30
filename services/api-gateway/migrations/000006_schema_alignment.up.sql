-- +goose Up

-- Keep JSON array fields consistent with the Go model types.
-- Earlier versions used PostgreSQL text[] for these two fields while the
-- application serializes StringArray as JSONB. Convert existing installations
-- safely so prompt package writes work after an upgrade as well as on fresh DBs.
ALTER TABLE prompt_packages
    ALTER COLUMN selected_models DROP DEFAULT,
    ALTER COLUMN selected_models TYPE JSONB USING to_jsonb(selected_models),
    ALTER COLUMN selected_models SET DEFAULT '[]'::jsonb;

ALTER TABLE model_configs
    ALTER COLUMN aspect_ratios DROP DEFAULT,
    ALTER COLUMN aspect_ratios TYPE JSONB USING to_jsonb(aspect_ratios),
    ALTER COLUMN aspect_ratios SET DEFAULT '[]'::jsonb;
