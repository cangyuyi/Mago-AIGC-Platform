-- +goose Down

DROP TABLE IF EXISTS brand_kits CASCADE;
DROP TABLE IF EXISTS prop_presets CASCADE;
DROP TABLE IF EXISTS scene_presets CASCADE;
DROP TABLE IF EXISTS style_combinations CASCADE;
DROP TABLE IF EXISTS character_ref_images CASCADE;
