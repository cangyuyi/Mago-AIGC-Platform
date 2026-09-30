package repository

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
	"mago-agent/api-gateway/internal/model"
)

type SceneRepository struct{ db *gorm.DB }

func NewSceneRepository(db *gorm.DB) *SceneRepository        { return &SceneRepository{db: db} }
func (r *SceneRepository) Create(s *model.ScenePreset) error { return r.db.Create(s).Error }
func (r *SceneRepository) FindByID(id uuid.UUID) (*model.ScenePreset, error) {
	var s model.ScenePreset
	err := r.db.Where("id = ?", id).First(&s).Error
	return &s, err
}
func (r *SceneRepository) List(ownerID uuid.UUID, category string, page, pageSize int) ([]model.ScenePreset, int64, error) {
	var ss []model.ScenePreset
	var total int64
	q := r.db.Where("(owner_id = ? OR is_preset = true)", ownerID)
	if category != "" && category != "all" {
		q = q.Where("category = ?", category)
	}
	if err := q.Model(&model.ScenePreset{}).Count(&total).Error; err != nil {
		return nil, 0, err
	}
	err := q.Order("is_preset DESC, updated_at DESC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&ss).Error
	return ss, total, err
}
func (r *SceneRepository) Update(s *model.ScenePreset) error { return r.db.Save(s).Error }
func (r *SceneRepository) Delete(id uuid.UUID) error {
	return r.db.Delete(&model.ScenePreset{}, "id = ?", id).Error
}
