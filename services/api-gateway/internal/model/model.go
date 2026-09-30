package model

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// JSONMap is a generic JSON column type for storing dynamic data
type JSONMap map[string]interface{}

func (m JSONMap) Value() (driver.Value, error) {
	if m == nil {
		return nil, nil
	}
	return json.Marshal(m)
}

func (m *JSONMap) Scan(value interface{}) error {
	if value == nil {
		*m = nil
		return nil
	}
	var data []byte
	switch v := value.(type) {
	case []byte:
		data = v
	case string:
		data = []byte(v)
	default:
		return errors.New("unsupported type for JSONMap")
	}
	return json.Unmarshal(data, m)
}

// JSONValue stores any valid JSON value, including arrays and scalar values.
// It is used for JSONB columns whose shape is intentionally dynamic.
type JSONValue struct {
	Data interface{}
}

func (v JSONValue) Value() (driver.Value, error) {
	if v.Data == nil {
		return nil, nil
	}
	return json.Marshal(v.Data)
}

func (v JSONValue) MarshalJSON() ([]byte, error) {
	if v.Data == nil {
		return []byte("null"), nil
	}
	return json.Marshal(v.Data)
}

func (v *JSONValue) UnmarshalJSON(data []byte) error {
	if string(data) == "null" {
		v.Data = nil
		return nil
	}
	var decoded interface{}
	if err := json.Unmarshal(data, &decoded); err != nil {
		return err
	}
	v.Data = decoded
	return nil
}

func (v *JSONValue) Scan(value interface{}) error {
	if value == nil {
		v.Data = nil
		return nil
	}
	var data []byte
	switch raw := value.(type) {
	case []byte:
		data = raw
	case string:
		data = []byte(raw)
	default:
		return fmt.Errorf("unsupported type for JSONValue: %T", value)
	}
	return v.UnmarshalJSON(data)
}

// StringArray is for PostgreSQL text[] columns
type StringArray []string

func (a StringArray) Value() (driver.Value, error) {
	if a == nil {
		return nil, nil
	}
	return json.Marshal(a)
}

func (a *StringArray) Scan(value interface{}) error {
	if value == nil {
		*a = nil
		return nil
	}
	var raw string
	switch v := value.(type) {
	case []byte:
		raw = string(v)
	case string:
		raw = v
	default:
		return fmt.Errorf("unsupported type for StringArray: %T", value)
	}
	if err := json.Unmarshal([]byte(raw), a); err == nil {
		return nil
	}
	// Accept legacy PostgreSQL text[] literals so databases created by
	// migration 000005 remain readable during an upgrade.
	if !strings.HasPrefix(raw, "{") || !strings.HasSuffix(raw, "}") {
		return fmt.Errorf("invalid StringArray value: %q", raw)
	}
	contents := raw[1 : len(raw)-1]
	if contents == "" {
		*a = StringArray{}
		return nil
	}
	items := strings.Split(contents, ",")
	for i := range items {
		items[i] = strings.Trim(items[i], `"`)
		items[i] = strings.ReplaceAll(items[i], `\\`, `\`)
		items[i] = strings.ReplaceAll(items[i], `\"`, `"`)
	}
	*a = StringArray(items)
	return nil
}

// BaseModel contains common columns
type BaseModel struct {
	ID        uuid.UUID      `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
}

// User represents a platform user
type User struct {
	BaseModel
	Email     string     `gorm:"uniqueIndex;not null;size:255" json:"email"`
	Password  string     `gorm:"not null" json:"-"` // Never serialize password
	Name      string     `gorm:"size:255;not null" json:"name"`
	AvatarURL string     `gorm:"size:512" json:"avatar_url,omitempty"`
	OrgID     *uuid.UUID `gorm:"type:uuid" json:"org_id,omitempty"`
	Role      string     `gorm:"size:32;default:'owner'" json:"role"`
}

// Organization represents a team/org
type Organization struct {
	BaseModel
	Name    string    `gorm:"size:255;not null" json:"name"`
	OwnerID uuid.UUID `gorm:"type:uuid;not null" json:"owner_id"`
}

// Membership maps users to orgs
type Membership struct {
	BaseModel
	UserID uuid.UUID `gorm:"type:uuid;not null;uniqueIndex:idx_user_org" json:"user_id"`
	OrgID  uuid.UUID `gorm:"type:uuid;not null;uniqueIndex:idx_user_org" json:"org_id"`
	Role   string    `gorm:"size:32;not null;default:'editor'" json:"role"` // owner/admin/editor/viewer
}

// Project represents a video creation project
type Project struct {
	BaseModel
	Name              string      `gorm:"size:255;not null" json:"name"`
	Description       string      `gorm:"type:text" json:"description,omitempty"`
	Status            string      `gorm:"size:32;default:'draft'" json:"status"`
	AspectRatio       string      `gorm:"size:16;default:'9:16'" json:"aspect_ratio"`
	TargetPlatform    string      `gorm:"size:64" json:"target_platform,omitempty"`
	TargetDuration    int         `json:"target_duration,omitempty"`
	Category          string      `gorm:"size:64" json:"category,omitempty"`
	CoverImageURL     string      `gorm:"size:512" json:"cover_image_url,omitempty"`
	OwnerID           uuid.UUID   `gorm:"type:uuid;not null;index" json:"owner_id"`
	OrgID             *uuid.UUID  `gorm:"type:uuid;index" json:"org_id,omitempty"`
	CurrentStep       string      `gorm:"size:32" json:"current_step,omitempty"`
	CharacterIDs      StringArray `gorm:"type:jsonb" json:"character_ids"`
	StylePresetIDs    StringArray `gorm:"type:jsonb" json:"style_preset_ids"`
	ReferenceVideoIDs StringArray `gorm:"type:jsonb" json:"reference_video_ids"`
}

// Script represents a video script
type Script struct {
	BaseModel
	ProjectID       uuid.UUID   `gorm:"type:uuid;not null;index" json:"project_id"`
	Version         int         `gorm:"not null;default:1" json:"version"`
	Title           string      `gorm:"size:512;not null" json:"title"`
	ScriptType      string      `gorm:"size:32;not null;default:'oral_sharing'" json:"script_type"`
	DurationTarget  int         `json:"duration_target,omitempty"`
	AspectRatio     string      `gorm:"size:16;default:'9:16'" json:"aspect_ratio"`
	TargetPlatform  string      `gorm:"size:64" json:"target_platform,omitempty"`
	Status          string      `gorm:"size:20;default:'draft'" json:"status"`
	Hook            string      `gorm:"type:text" json:"hook,omitempty"`
	HookType        string      `gorm:"size:64" json:"hook_type,omitempty"`
	Body            string      `gorm:"type:text" json:"body,omitempty"`
	CTA             string      `gorm:"type:text" json:"cta,omitempty"`
	CTAType         string      `gorm:"size:64" json:"cta_type,omitempty"`
	Tags            StringArray `gorm:"type:jsonb" json:"tags"`
	EmotionArc      StringArray `gorm:"type:jsonb" json:"emotion_arc"`
	QualityScores   JSONMap     `gorm:"type:jsonb" json:"quality_scores"`
	QualityFeedback JSONMap     `gorm:"type:jsonb" json:"quality_feedback"`
	ComplianceFlags JSONMap     `gorm:"type:jsonb" json:"compliance_flags"`
	CreativeBrief   JSONMap     `gorm:"type:jsonb" json:"creative_brief"`
	ModelInfo       JSONMap     `gorm:"type:jsonb" json:"model_info"`
}

// Storyboard represents a collection of shots
type Storyboard struct {
	BaseModel
	ProjectID     uuid.UUID `gorm:"type:uuid;not null;index" json:"project_id"`
	ScriptID      uuid.UUID `gorm:"type:uuid;not null;index" json:"script_id"`
	Version       int       `gorm:"not null;default:1" json:"version"`
	Title         string    `gorm:"size:255" json:"title"`
	TotalDuration float64   `json:"total_duration"`
	ShotCount     int       `json:"shot_count"`
	AspectRatio   string    `gorm:"size:16;default:'9:16'" json:"aspect_ratio"`
	Status        string    `gorm:"size:20;default:'draft'" json:"status"`
	ModelInfo     JSONMap   `gorm:"type:jsonb" json:"model_info"`
}

// StoryboardShot represents a single shot in a storyboard
type StoryboardShot struct {
	BaseModel
	StoryboardID       uuid.UUID   `gorm:"type:uuid;not null;index" json:"storyboard_id"`
	ShotIndex          int         `gorm:"not null" json:"shot_index"`
	Duration           float64     `gorm:"not null" json:"duration"`
	ShotType           string      `gorm:"size:32" json:"shot_type,omitempty"`
	CameraMovement     string      `gorm:"size:64" json:"camera_movement,omitempty"`
	CameraAngle        string      `gorm:"size:32" json:"camera_angle,omitempty"`
	SceneEnvironment   string      `gorm:"type:text;not null" json:"scene_environment"`
	SubjectDescription string      `gorm:"type:text;not null" json:"subject_description"`
	Props              StringArray `gorm:"type:jsonb" json:"props"`
	Lighting           string      `gorm:"type:text" json:"lighting,omitempty"`
	ColorTone          string      `gorm:"type:text" json:"color_tone,omitempty"`
	Composition        string      `gorm:"type:text" json:"composition,omitempty"`
	DialogueNarration  string      `gorm:"type:text" json:"dialogue_narration,omitempty"`
	SoundEffect        string      `gorm:"type:text" json:"sound_effect,omitempty"`
	BGMEmotion         string      `gorm:"size:64" json:"bgm_emotion,omitempty"`
	EmotionTag         string      `gorm:"size:32" json:"emotion_tag,omitempty"`
	TransitionIn       string      `gorm:"size:32" json:"transition_in,omitempty"`
	TransitionOut      string      `gorm:"size:32" json:"transition_out,omitempty"`
	MotionDescription  string      `gorm:"type:text" json:"motion_description,omitempty"`
	AIGenerationNotes  string      `gorm:"type:text" json:"ai_generation_notes,omitempty"`
	ConsistencyHints   JSONMap     `gorm:"type:jsonb" json:"consistency_hints"`
	QualityScore       int         `json:"quality_score,omitempty"`
	Feedback           string      `gorm:"type:text" json:"feedback,omitempty"`
}

// Character (defined but detail endpoints come in 04-character-style)
type Character struct {
	BaseModel
	OwnerID             uuid.UUID   `gorm:"type:uuid;index" json:"owner_id"`
	OrgID               *uuid.UUID  `gorm:"type:uuid;index" json:"org_id,omitempty"`
	Visibility          string      `gorm:"size:16;default:'private'" json:"visibility"`
	Name                string      `gorm:"size:128;not null" json:"name"`
	Description         string      `gorm:"type:text" json:"description,omitempty"`
	Gender              string      `gorm:"size:16" json:"gender,omitempty"`
	AgeAppearance       string      `gorm:"size:32" json:"age_appearance,omitempty"`
	Ethnicity           string      `gorm:"size:32" json:"ethnicity,omitempty"`
	FaceDesc            string      `gorm:"type:text" json:"face_description,omitempty"`
	HairDesc            string      `gorm:"type:text" json:"hair_description,omitempty"`
	BodyDesc            string      `gorm:"type:text" json:"body_description,omitempty"`
	ClothingDefault     string      `gorm:"type:text" json:"clothing_default,omitempty"`
	SkinDetails         string      `gorm:"type:text" json:"skin_details,omitempty"`
	DistinctiveFeatures StringArray `gorm:"type:jsonb" json:"distinctive_features"`
	PersonalityVibe     string      `gorm:"size:128" json:"personality_vibe,omitempty"`
	FaceIDWeight        float64     `gorm:"default:0.8" json:"faceid_weight"`
	IPAdapterScale      float64     `gorm:"default:0.7" json:"ip_adapter_scale"`
	RefStrategy         string      `gorm:"size:32;default:'faceid'" json:"reference_strategy"`
	SeedBase            int         `json:"seed_base,omitempty"`
	ModelCompat         JSONMap     `gorm:"type:jsonb" json:"model_compatibility"`
	PromptFragment      string      `gorm:"type:text;not null" json:"prompt_fragment"`
	NegativeFrag        string      `gorm:"type:text" json:"negative_fragment,omitempty"`
	Tags                StringArray `gorm:"type:jsonb" json:"tags"`
	IsPreset            bool        `gorm:"default:false" json:"is_preset"`
	UsageCount          int         `gorm:"default:0" json:"usage_count"`
}

// StylePreset (defined but detail endpoints come in 04)
type StylePreset struct {
	BaseModel
	OwnerID        *uuid.UUID  `gorm:"type:uuid;index" json:"owner_id"`
	OrgID          *uuid.UUID  `gorm:"type:uuid;index" json:"org_id,omitempty"`
	Visibility     string      `gorm:"size:16;default:'private'" json:"visibility"`
	Name           string      `gorm:"size:128;not null" json:"name"`
	Category       string      `gorm:"size:32;not null" json:"category"`
	Description    string      `gorm:"type:text" json:"description,omitempty"`
	PositiveFrag   string      `gorm:"type:text;not null" json:"positive_fragment"`
	NegativeFrag   string      `gorm:"type:text" json:"negative_fragment,omitempty"`
	DominantColors StringArray `gorm:"type:jsonb" json:"dominant_colors"`
	LightingStyle  string      `gorm:"size:64" json:"lighting_style,omitempty"`
	ColorTone      string      `gorm:"size:64" json:"color_tone,omitempty"`
	LensCamera     string      `gorm:"size:128" json:"lens_and_camera,omitempty"`
	ParamHints     JSONMap     `gorm:"type:jsonb" json:"parameter_hints"`
	RecLoRAs       JSONMap     `gorm:"type:jsonb" json:"recommended_loras"`
	ExampleImgURL  string      `gorm:"size:512" json:"example_image_url,omitempty"`
	Tags           StringArray `gorm:"type:jsonb" json:"tags"`
	IsPreset       bool        `gorm:"default:false" json:"is_preset"`
	UsageCount     int         `gorm:"default:0" json:"usage_count"`
}

// TrendTopic (for hot trends, detail in 02)
type TrendTopic struct {
	BaseModel
	Platform        string      `gorm:"size:32;not null" json:"platform"`
	TopicID         string      `gorm:"size:255" json:"topic_id,omitempty"`
	Title           string      `gorm:"size:512;not null" json:"title"`
	Category        string      `gorm:"size:64" json:"category,omitempty"`
	HotValue        int64       `json:"hot_value,omitempty"`
	HotValueGrowth  float64     `json:"hot_value_growth,omitempty"`
	RankPosition    int         `json:"rank_position,omitempty"`
	CoverURL        string      `gorm:"size:512" json:"cover_url,omitempty"`
	URL             string      `gorm:"type:text" json:"url,omitempty"`
	Tags            StringArray `gorm:"type:jsonb" json:"tags"`
	Status          string      `gorm:"size:20;default:'rising'" json:"status"`
	LifecycleStage  string      `gorm:"size:32" json:"lifecycle_stage,omitempty"`
	RelatedVideosCt int         `gorm:"default:0" json:"related_videos_count"`
	FirstSeenAt     *time.Time  `json:"first_seen_at,omitempty"`
	LastUpdatedAt   time.Time   `json:"last_updated_at"`
	HotValueHistory JSONMap     `gorm:"type:jsonb" json:"hot_value_history"`
	RelatedVideoIDs StringArray `gorm:"type:jsonb" json:"related_video_ids"`
	Extra           JSONMap     `gorm:"type:jsonb" json:"extra"`
}

// ViralVideo (for viral video storage, detail in 02)
type ViralVideo struct {
	BaseModel
	Platform        string      `gorm:"size:32;not null;uniqueIndex:idx_vid_platform_vid" json:"platform"`
	VideoID         string      `gorm:"size:255;not null;uniqueIndex:idx_vid_platform_vid" json:"video_id"`
	URL             string      `gorm:"type:text;not null" json:"url"`
	AuthorName      string      `gorm:"size:255" json:"author_name,omitempty"`
	Title           string      `gorm:"size:512" json:"title,omitempty"`
	Description     string      `gorm:"type:text" json:"description,omitempty"`
	Tags            StringArray `gorm:"type:jsonb" json:"tags"`
	Category        string      `gorm:"size:64" json:"category,omitempty"`
	Duration        float64     `json:"duration,omitempty"`
	Width           int         `json:"width,omitempty"`
	Height          int         `json:"height,omitempty"`
	AspectRatio     string      `gorm:"size:16" json:"aspect_ratio,omitempty"`
	Metrics         JSONMap     `gorm:"type:jsonb" json:"metrics"`
	ViralScore      float64     `json:"viral_score,omitempty"`
	AnalysisStatus  string      `gorm:"size:20;default:'pending'" json:"analysis_status"`
	AnalysisErr     string      `gorm:"type:text" json:"analysis_error,omitempty"`
	ThumbnailURL    string      `gorm:"size:512" json:"thumbnail_url,omitempty"`
	BGMName         string      `gorm:"size:255" json:"bgm_name,omitempty"`
	BGMBPM          float64     `json:"bgm_bpm,omitempty"`
	BGMEmotion      string      `gorm:"size:64" json:"bgm_emotion,omitempty"`
	Transcript      string      `gorm:"type:text" json:"transcript,omitempty"`
	ASRLanguage     string      `gorm:"size:16" json:"asr_language,omitempty"`
	ShotCount       int         `gorm:"default:0" json:"shot_count,omitempty"`
	AvgShotDuration float64     `json:"avg_shot_duration,omitempty"`
	HookText        string      `gorm:"type:text" json:"hook_text,omitempty"`
	HookType        string      `gorm:"size:64" json:"hook_type,omitempty"`
	HookEngagement  float64     `json:"hook_engagement_score,omitempty"`
	NarrativeStruct JSONMap     `gorm:"type:jsonb;column:narrative_structure" json:"narrative_structure"`
	VisualLanguage  JSONMap     `gorm:"type:jsonb" json:"visual_language"`
	RhythmAnalysis  JSONMap     `gorm:"type:jsonb" json:"rhythm_analysis"`
	EmotionCurve    JSONValue   `gorm:"type:jsonb" json:"emotion_curve"`
	KeyframeURLs    StringArray `gorm:"type:jsonb" json:"keyframe_urls"`
	PatternIDs      StringArray `gorm:"type:jsonb" json:"pattern_ids"`
	AnalyzedAt      *time.Time  `json:"analyzed_at,omitempty"`
	AnalysisVersion string      `gorm:"size:32;default:'v1'" json:"analysis_version,omitempty"`
	ExtraMetadata   JSONMap     `gorm:"type:jsonb" json:"extra_metadata"`
	Analysis        JSONMap     `gorm:"type:jsonb" json:"analysis"`
	Shots           []VideoShot `gorm:"foreignKey:ViralVideoID" json:"shots,omitempty"`
}

// CreativeSession tracks agent creative process
type CreativeSession struct {
	BaseModel
	ProjectID   uuid.UUID `gorm:"type:uuid;not null;index" json:"project_id"`
	SessionType string    `gorm:"size:32;not null" json:"session_type"`
	Status      string    `gorm:"size:20;default:'active'" json:"status"`
	Ideas       JSONMap   `gorm:"type:jsonb" json:"ideas"`
	SelectedID  string    `gorm:"size:64" json:"selected_idea_id,omitempty"`
	DebateLog   JSONMap   `gorm:"type:jsonb" json:"debate_log"`
}

// VideoShot represents an individual shot within a viral video analysis
type VideoShot struct {
	BaseModel
	ViralVideoID    uuid.UUID   `gorm:"type:uuid;not null;index" json:"viral_video_id"`
	ShotIndex       int         `gorm:"not null" json:"shot_index"`
	StartTime       float64     `gorm:"not null" json:"start_time"`
	EndTime         float64     `gorm:"not null" json:"end_time"`
	Duration        float64     `gorm:"not null" json:"duration"`
	KeyframeURL     string      `gorm:"size:512" json:"keyframe_url,omitempty"`
	KeyframePath    string      `gorm:"size:512" json:"-"`
	Transcript      string      `gorm:"type:text" json:"transcript,omitempty"`
	TranscriptWords JSONMap     `gorm:"type:jsonb" json:"transcript_words"`
	VisualDesc      string      `gorm:"type:text" json:"visual_description,omitempty"`
	VisualTags      StringArray `gorm:"type:jsonb" json:"visual_tags"`
	CameraMovement  string      `gorm:"size:64" json:"camera_movement,omitempty"`
	CameraAngle     string      `gorm:"size:32" json:"camera_angle,omitempty"`
	Lighting        string      `gorm:"size:64" json:"lighting,omitempty"`
	ColorPalette    JSONMap     `gorm:"type:jsonb" json:"color_palette"`
	EmotionTag      string      `gorm:"size:32" json:"emotion_tag,omitempty"`
	TextOCR         string      `gorm:"type:text" json:"text_ocr,omitempty"`
	TransitionType  string      `gorm:"size:32" json:"transition_type,omitempty"`
	HasFace         bool        `gorm:"default:false" json:"has_face"`
	FaceCount       int         `gorm:"default:0" json:"face_count"`
	MotionIntensity float64     `gorm:"default:0" json:"motion_intensity"`
	AudioType       string      `gorm:"size:32" json:"audio_type,omitempty"`
	OnsetStrength   float64     `gorm:"default:0" json:"onset_strength"`
	ObjectsDetected JSONMap     `gorm:"type:jsonb" json:"objects_detected"`
	QualityScore    float64     `gorm:"default:0" json:"quality_score"`
	HotValueHistory JSONMap     `gorm:"type:jsonb" json:"hot_value_history"`
	RelatedVideoIDs StringArray `gorm:"type:jsonb" json:"related_video_ids"`
	Extra           JSONMap     `gorm:"type:jsonb" json:"extra"`
}

// ViralPattern represents an extracted viral video formula/pattern
type ViralPattern struct {
	BaseModel
	Name                    string      `gorm:"size:255;not null" json:"name"`
	PatternType             string      `gorm:"size:64;not null;index" json:"pattern_type"`
	Category                string      `gorm:"size:64;index" json:"category,omitempty"`
	Description             string      `gorm:"type:text;not null" json:"description"`
	FormulaTemplate         string      `gorm:"type:text" json:"formula_template,omitempty"`
	AvgViralScore           float64     `gorm:"default:0" json:"avg_viral_score"`
	SampleCount             int         `gorm:"default:0" json:"sample_count"`
	ExampleVideoIDs         StringArray `gorm:"type:jsonb" json:"example_video_ids"`
	TriggerConditions       JSONMap     `gorm:"type:jsonb" json:"trigger_conditions"`
	ApplicablePlatforms     StringArray `gorm:"type:jsonb" json:"applicable_platforms"`
	ApplicableDurationRange JSONMap     `gorm:"type:jsonb" json:"applicable_duration_range"`
	KeyVisuals              StringArray `gorm:"type:jsonb" json:"key_visuals"`
	KeyPhrases              StringArray `gorm:"type:jsonb" json:"key_phrases"`
	AudioCharacteristics    JSONMap     `gorm:"type:jsonb" json:"audio_characteristics"`
	EditingCharacteristics  JSONMap     `gorm:"type:jsonb" json:"editing_characteristics"`
	SuccessRate             float64     `gorm:"default:0" json:"success_rate"`
	Tags                    StringArray `gorm:"type:jsonb" json:"tags"`
	IsVerified              bool        `gorm:"default:false;index" json:"is_verified"`
	Source                  string      `gorm:"size:32;default:'ai_extracted'" json:"source"`
	Extra                   JSONMap     `gorm:"type:jsonb" json:"extra"`
}

// CharacterRefImage is a reference image for a character.
type CharacterRefImage struct {
	BaseModel
	CharacterID  uuid.UUID `gorm:"type:uuid;not null;index" json:"character_id"`
	ImageType    string    `gorm:"size:32;not null" json:"image_type"`
	ImageURL     string    `gorm:"size:512;not null" json:"image_url"`
	ThumbnailURL string    `gorm:"size:512" json:"thumbnail_url,omitempty"`
	Width        int       `json:"width,omitempty"`
	Height       int       `json:"height,omitempty"`
	AIDesc       string    `gorm:"type:text" json:"ai_description,omitempty"`
	SortOrder    int       `gorm:"default:0" json:"sort_order"`
}

// StyleCombination combines multiple style presets.
type StyleCombination struct {
	BaseModel
	OwnerID         uuid.UUID `gorm:"type:uuid;not null;index" json:"owner_id"`
	Name            string    `gorm:"size:128;not null" json:"name"`
	StyleIDs        JSONMap   `gorm:"type:jsonb;not null" json:"style_ids"`
	MergedPositive  string    `gorm:"type:text" json:"merged_positive_fragment,omitempty"`
	MergedNegative  string    `gorm:"type:text" json:"merged_negative_fragment,omitempty"`
	MergedParams    JSONMap   `gorm:"type:jsonb" json:"merged_parameter_hints"`
	PreviewImageURL string    `gorm:"size:512" json:"preview_image_url,omitempty"`
}

// ScenePreset is a reusable scene/location preset.
type ScenePreset struct {
	BaseModel
	OwnerID         *uuid.UUID  `gorm:"type:uuid;index" json:"owner_id,omitempty"`
	Category        string      `gorm:"size:64;not null" json:"category"`
	Name            string      `gorm:"size:128;not null" json:"name"`
	Description     string      `gorm:"type:text;not null" json:"description"`
	PromptFragment  string      `gorm:"type:text;not null" json:"prompt_fragment"`
	LightingDefault string      `gorm:"size:128" json:"lighting_default,omitempty"`
	TimeOfDay       string      `gorm:"size:32" json:"time_of_day,omitempty"`
	Weather         string      `gorm:"size:32" json:"weather,omitempty"`
	Era             string      `gorm:"size:64" json:"era,omitempty"`
	Geography       string      `gorm:"size:64" json:"geography,omitempty"`
	RefImageURL     string      `gorm:"size:512" json:"reference_image_url,omitempty"`
	Tags            StringArray `gorm:"type:jsonb" json:"tags"`
	IsPreset        bool        `gorm:"default:false" json:"is_preset"`
}

// PropPreset is a reusable prop/object preset.
type PropPreset struct {
	BaseModel
	OwnerID        *uuid.UUID  `gorm:"type:uuid;index" json:"owner_id,omitempty"`
	Category       string      `gorm:"size:64" json:"category,omitempty"`
	Name           string      `gorm:"size:128;not null" json:"name"`
	Description    string      `gorm:"type:text;not null" json:"description"`
	PromptFragment string      `gorm:"type:text;not null" json:"prompt_fragment"`
	Era            string      `gorm:"size:64" json:"era,omitempty"`
	Material       string      `gorm:"size:64" json:"material,omitempty"`
	Size           string      `gorm:"size:32" json:"size,omitempty"`
	RefImageURL    string      `gorm:"size:512" json:"reference_image_url,omitempty"`
	Tags           StringArray `gorm:"type:jsonb" json:"tags"`
	IsPreset       bool        `gorm:"default:false" json:"is_preset"`
}

// PromptPackage groups prompts for a storyboard export.
type PromptPackage struct {
	BaseModel
	ProjectID      uuid.UUID   `gorm:"type:uuid;not null;index" json:"project_id"`
	StoryboardID   uuid.UUID   `gorm:"type:uuid;not null;index" json:"storyboard_id"`
	Version        int         `gorm:"not null;default:1" json:"version"`
	Name           string      `gorm:"size:255" json:"name"`
	Status         string      `gorm:"size:20;default:'draft'" json:"status"`
	TotalShots     int         `json:"total_shots"`
	SelectedModels StringArray `gorm:"type:jsonb" json:"selected_models"`
	GlobalParams   JSONMap     `gorm:"type:jsonb" json:"global_parameters"`
}

// Prompt is a single generated prompt for one shot+model combination.
type Prompt struct {
	BaseModel
	PackageID        uuid.UUID `gorm:"type:uuid;not null;index" json:"package_id"`
	ShotID           uuid.UUID `gorm:"type:uuid;not null;index" json:"shot_id"`
	ModelID          string    `gorm:"size:64;not null;index" json:"model_id"`
	PromptType       string    `gorm:"size:16;not null;default:'video'" json:"prompt_type"`
	PositivePrompt   string    `gorm:"type:text;not null" json:"positive_prompt"`
	NegativePrompt   string    `gorm:"type:text" json:"negative_prompt,omitempty"`
	Parameters       JSONMap   `gorm:"type:jsonb" json:"parameters"`
	ReferenceImages  JSONValue `gorm:"type:jsonb" json:"reference_images"`
	LoraTriggers     JSONValue `gorm:"type:jsonb" json:"lora_triggers"`
	SeedValue        int       `json:"seed_value,omitempty"`
	SeedLocked       bool      `gorm:"default:false" json:"seed_locked"`
	ConsistencyNotes string    `gorm:"type:text" json:"consistency_notes,omitempty"`
	Version          int       `gorm:"not null;default:1" json:"version"`
	QualityScore     JSONMap   `gorm:"type:jsonb" json:"quality_score"`
	ExportedToMago   bool      `gorm:"default:false" json:"exported_to_mago"`
	UserModified     bool      `gorm:"default:false" json:"user_modified"`
	CreatedBy        string    `gorm:"size:16;default:'agent'" json:"created_by"`
}

// ModelConfig describes an image/video model supported by the prompt engine.
type ModelConfig struct {
	BaseModel
	ModelID                string      `gorm:"size:64;not null;uniqueIndex" json:"model_id"`
	DisplayName            string      `gorm:"size:128;not null" json:"display_name"`
	Vendor                 string      `gorm:"size:64;not null" json:"vendor"`
	PromptType             string      `gorm:"size:16;not null" json:"prompt_type"`
	MaxLength              int         `gorm:"default:500" json:"max_length"`
	Language               string      `gorm:"size:16;default:'en'" json:"language"`
	SupportsNegative       bool        `gorm:"default:true" json:"supports_negative"`
	SupportsReferenceImage bool        `gorm:"default:false" json:"supports_reference_images"`
	SupportsSeed           bool        `gorm:"default:true" json:"supports_seed"`
	SupportsCFG            bool        `gorm:"default:true" json:"supports_cfg"`
	AspectRatios           StringArray `gorm:"type:jsonb" json:"aspect_ratios"`
	DefaultParameters      JSONMap     `gorm:"type:jsonb" json:"default_parameters"`
	QualityBooster         string      `gorm:"type:text" json:"quality_booster,omitempty"`
	UniversalNegative      string      `gorm:"type:text" json:"universal_negative,omitempty"`
	ParameterRules         JSONMap     `gorm:"type:jsonb" json:"parameter_rules"`
	IsActive               bool        `gorm:"default:true" json:"is_active"`
	SortOrder              int         `gorm:"default:0" json:"sort_order"`
}

// BrandKit is an organization brand visual guideline.
type BrandKit struct {
	BaseModel
	OrgID             uuid.UUID   `gorm:"type:uuid;not null" json:"org_id"`
	Name              string      `gorm:"size:128;not null" json:"name"`
	BrandColors       StringArray `gorm:"type:jsonb" json:"brand_colors"`
	LogoURL           string      `gorm:"size:512" json:"logo_url,omitempty"`
	FontPrefs         JSONMap     `gorm:"type:jsonb" json:"font_preferences"`
	VisualTone        string      `gorm:"size:128" json:"visual_tone,omitempty"`
	ForbiddenElements StringArray `gorm:"type:jsonb" json:"forbidden_elements"`
}

// CrawlTask tracks crawler job execution
type CrawlTask struct {
	BaseModel
	Platform     string     `gorm:"size:32;not null;index" json:"platform"`
	TaskType     string     `gorm:"size:32;not null;index" json:"task_type"`
	Status       string     `gorm:"size:20;default:'pending';index" json:"status"`
	StartedAt    *time.Time `json:"started_at,omitempty"`
	FinishedAt   *time.Time `json:"finished_at,omitempty"`
	ItemsFound   int        `gorm:"default:0" json:"items_found"`
	ItemsNew     int        `gorm:"default:0" json:"items_new"`
	ItemsUpdated int        `gorm:"default:0" json:"items_updated"`
	ItemsFailed  int        `gorm:"default:0" json:"items_failed"`
	ErrorMessage string     `gorm:"type:text" json:"error_message,omitempty"`
	ProxyUsed    string     `gorm:"size:128" json:"proxy_used,omitempty"`
	CrawlParams  JSONMap    `gorm:"type:jsonb" json:"crawl_params"`
	DurationMs   int        `gorm:"default:0" json:"duration_ms"`
	TriggeredBy  string     `gorm:"size:32;default:'scheduler'" json:"triggered_by"`
	WorkerID     string     `gorm:"size:64" json:"worker_id,omitempty"`
	Extra        JSONMap    `gorm:"type:jsonb" json:"extra"`
}

// TopicRecommendation stores generated topic recommendation results
type TopicRecommendation struct {
	BaseModel
	UserID             *uuid.UUID  `gorm:"type:uuid;index" json:"user_id,omitempty"`
	OrgID              *uuid.UUID  `gorm:"type:uuid;index" json:"org_id,omitempty"`
	Category           string      `gorm:"size:64" json:"category,omitempty"`
	Keywords           StringArray `gorm:"type:jsonb" json:"keywords"`
	ReferenceVideoURLs StringArray `gorm:"type:jsonb" json:"reference_video_urls"`
	Topics             JSONValue   `gorm:"type:jsonb;not null" json:"topics"`
	ModelInfo          JSONMap     `gorm:"type:jsonb" json:"model_info"`
	Feedback           JSONMap     `gorm:"type:jsonb" json:"feedback"`
}
