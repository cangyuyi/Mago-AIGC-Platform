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

-- +goose Down
-- PostgreSQL does not allow a subquery directly in ALTER COLUMN ... USING.
-- Put the JSONB set-returning expansion in a temporary migration helper
-- function so rollback works on PostgreSQL 16 as well as on fresh schemas.
CREATE FUNCTION _mago_000006_jsonb_array_to_text_array(payload JSONB)
RETURNS TEXT[]
LANGUAGE SQL
IMMUTABLE
STRICT
AS $$
    SELECT ARRAY(
        SELECT element
        FROM jsonb_array_elements_text(payload) WITH ORDINALITY AS items(element, ordinal)
        ORDER BY ordinal
    );
$$;

ALTER TABLE prompt_packages
    ALTER COLUMN selected_models DROP DEFAULT,
    ALTER COLUMN selected_models TYPE TEXT[] USING _mago_000006_jsonb_array_to_text_array(selected_models),
    ALTER COLUMN selected_models SET DEFAULT '{}'::text[];

ALTER TABLE model_configs
    ALTER COLUMN aspect_ratios DROP DEFAULT,
    ALTER COLUMN aspect_ratios TYPE TEXT[] USING _mago_000006_jsonb_array_to_text_array(aspect_ratios),
    ALTER COLUMN aspect_ratios SET DEFAULT '{}'::text[];

DROP FUNCTION _mago_000006_jsonb_array_to_text_array(JSONB);
