-- +goose Up

-- 04 板块：角色与风格管理扩展表

-- 角色参考图片
CREATE TABLE IF NOT EXISTS character_ref_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    image_type VARCHAR(32) NOT NULL,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    width INT,
    height INT,
    ai_description TEXT,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_char_images_char ON character_ref_images(character_id);

-- 风格组合（多个风格叠加）
CREATE TABLE IF NOT EXISTS style_combinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(128) NOT NULL,
    style_ids JSONB NOT NULL DEFAULT '[]',
    merged_positive_fragment TEXT,
    merged_negative_fragment TEXT,
    merged_parameter_hints JSONB DEFAULT '{}',
    preview_image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_style_combos_owner ON style_combinations(owner_id);

-- 场景预设
CREATE TABLE IF NOT EXISTS scene_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    category VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    prompt_fragment TEXT NOT NULL,
    lighting_default VARCHAR(128),
    time_of_day VARCHAR(32),
    weather VARCHAR(32),
    era VARCHAR(64),
    geography VARCHAR(64),
    reference_image_url TEXT,
    tags JSONB DEFAULT '[]',
    is_preset BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 道具预设
CREATE TABLE IF NOT EXISTS prop_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    category VARCHAR(64),
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    prompt_fragment TEXT NOT NULL,
    era VARCHAR(64),
    material VARCHAR(64),
    size VARCHAR(32),
    reference_image_url TEXT,
    tags JSONB DEFAULT '[]',
    is_preset BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 品牌视觉规范
CREATE TABLE IF NOT EXISTS brand_kits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(128) NOT NULL,
    brand_colors JSONB DEFAULT '[]',
    logo_url TEXT,
    font_preferences JSONB DEFAULT '{}',
    visual_tone VARCHAR(128),
    forbidden_elements JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
