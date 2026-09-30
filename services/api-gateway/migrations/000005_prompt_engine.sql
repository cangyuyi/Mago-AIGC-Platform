-- +goose Up
-- 05 板块：提示词引擎
CREATE TABLE IF NOT EXISTS prompt_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    storyboard_id UUID NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'draft',
    total_shots INT,
    selected_models JSONB DEFAULT '[]',
    global_parameters JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_prompt_pkg_project ON prompt_packages(project_id);
CREATE INDEX IF NOT EXISTS idx_prompt_pkg_storyboard ON prompt_packages(storyboard_id);
CREATE INDEX IF NOT EXISTS idx_prompt_pkg_created_at ON prompt_packages(created_at DESC);

CREATE TABLE IF NOT EXISTS prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES prompt_packages(id) ON DELETE CASCADE,
    shot_id UUID NOT NULL REFERENCES storyboard_shots(id) ON DELETE CASCADE,
    model_id VARCHAR(64) NOT NULL,
    prompt_type VARCHAR(16) NOT NULL DEFAULT 'video',
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT,
    parameters JSONB DEFAULT '{}',
    reference_images JSONB DEFAULT '[]',
    lora_triggers JSONB DEFAULT '[]',
    seed_value INT,
    seed_locked BOOLEAN DEFAULT false,
    consistency_notes TEXT,
    version INT NOT NULL DEFAULT 1,
    parent_prompt_id UUID REFERENCES prompts(id),
    iteration_note TEXT,
    quality_score JSONB DEFAULT '{}',
    quality_feedback JSONB DEFAULT '[]',
    exported_to_mago BOOLEAN DEFAULT false,
    mago_task_id UUID,
    user_modified BOOLEAN DEFAULT false,
    created_by VARCHAR(16) DEFAULT 'agent',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_prompts_package ON prompts(package_id);
CREATE INDEX IF NOT EXISTS idx_prompts_shot ON prompts(shot_id);
CREATE INDEX IF NOT EXISTS idx_prompts_model ON prompts(model_id);

CREATE TABLE IF NOT EXISTS model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128) NOT NULL,
    vendor VARCHAR(64) NOT NULL,
    prompt_type VARCHAR(16) NOT NULL,
    max_length INT DEFAULT 500,
    language VARCHAR(16) DEFAULT 'en',
    supports_negative BOOLEAN DEFAULT true,
    supports_reference_images BOOLEAN DEFAULT false,
    supports_seed BOOLEAN DEFAULT true,
    supports_cfg BOOLEAN DEFAULT true,
    aspect_ratios JSONB DEFAULT '[]',
    default_parameters JSONB DEFAULT '{}',
    quality_booster TEXT,
    universal_negative TEXT,
    parameter_rules JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- +goose Down
DROP INDEX IF EXISTS idx_prompt_pkg_created_at;
DROP TABLE IF EXISTS model_configs CASCADE;
DROP TABLE IF EXISTS prompts CASCADE;
DROP TABLE IF EXISTS prompt_packages CASCADE;
