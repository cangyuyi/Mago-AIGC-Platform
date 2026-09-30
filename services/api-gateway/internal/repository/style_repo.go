package repository

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
	"mago-agent/api-gateway/internal/model"
)

type StyleRepository struct{ db *gorm.DB }

func NewStyleRepository(db *gorm.DB) *StyleRepository { return &StyleRepository{db: db} }

func (r *StyleRepository) Create(s *model.StylePreset) error { return r.db.Create(s).Error }

func (r *StyleRepository) FindByID(id uuid.UUID) (*model.StylePreset, error) {
	var s model.StylePreset
	if err := r.db.Where("id = ?", id).First(&s).Error; err != nil {
		return nil, err
	}
	return &s, nil
}

// FindVisibleByOwner returns a style owned by the user or a system preset.
func (r *StyleRepository) FindVisibleByOwner(id, ownerID uuid.UUID) (*model.StylePreset, error) {
	var s model.StylePreset
	if err := r.db.Where("id = ? AND (owner_id = ? OR is_preset = true)", id, ownerID).First(&s).Error; err != nil {
		return nil, err
	}
	return &s, nil
}

func (r *StyleRepository) ListByOwnerOrPreset(ownerID uuid.UUID, category string, page, pageSize int) ([]model.StylePreset, int64, error) {
	var ss []model.StylePreset
	var total int64
	q := r.db.Where("(owner_id = ? OR is_preset = true)", ownerID)
	if category != "" && category != "all" {
		q = q.Where("category = ?", category)
	}
	if err := q.Model(&model.StylePreset{}).Count(&total).Error; err != nil {
		return nil, 0, err
	}
	if err := q.Order("is_preset DESC, updated_at DESC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&ss).Error; err != nil {
		return nil, 0, err
	}
	return ss, total, nil
}

func (r *StyleRepository) Update(s *model.StylePreset) error { return r.db.Save(s).Error }

// UpdateOwned updates only user-owned, non-preset styles. Protected ownership and
// preset fields are intentionally not taken from the request payload.
func (r *StyleRepository) UpdateOwned(s *model.StylePreset, ownerID uuid.UUID) error {
	result := r.db.Model(&model.StylePreset{}).
		Where("id = ? AND owner_id = ? AND is_preset = false", s.ID, ownerID).
		Updates(map[string]interface{}{
			"name":            s.Name,
			"category":        s.Category,
			"description":     s.Description,
			"visibility":      s.Visibility,
			"positive_frag":   s.PositiveFrag,
			"negative_frag":   s.NegativeFrag,
			"dominant_colors": s.DominantColors,
			"lighting_style":  s.LightingStyle,
			"color_tone":      s.ColorTone,
			"lens_camera":     s.LensCamera,
			"param_hints":     s.ParamHints,
			"rec_lo_r_as":     s.RecLoRAs,
			"example_img_url": s.ExampleImgURL,
			"tags":            s.Tags,
		})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}

func (r *StyleRepository) Delete(id uuid.UUID) error {
	result := r.db.Delete(&model.StylePreset{}, "id = ?", id)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}

func (r *StyleRepository) DeleteOwned(id, ownerID uuid.UUID) error {
	result := r.db.Where("id = ? AND owner_id = ? AND is_preset = false", id, ownerID).Delete(&model.StylePreset{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}

func (r *StyleRepository) ListCategories(ownerID uuid.UUID) ([]string, error) {
	var cats []string
	if err := r.db.Model(&model.StylePreset{}).Where("(owner_id = ? OR is_preset = true)", ownerID).Distinct("category").Pluck("category", &cats).Error; err != nil {
		return nil, err
	}
	return cats, nil
}
