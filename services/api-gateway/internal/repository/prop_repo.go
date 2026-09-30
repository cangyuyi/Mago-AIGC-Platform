package repository

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
	"mago-agent/api-gateway/internal/model"
)

type PropRepository struct{ db *gorm.DB }

func NewPropRepository(db *gorm.DB) *PropRepository        { return &PropRepository{db: db} }
func (r *PropRepository) Create(p *model.PropPreset) error { return r.db.Create(p).Error }
func (r *PropRepository) FindByID(id uuid.UUID) (*model.PropPreset, error) {
	var p model.PropPreset
	err := r.db.Where("id = ?", id).First(&p).Error
	return &p, err
}
func (r *PropRepository) List(ownerID uuid.UUID, category string, page, pageSize int) ([]model.PropPreset, int64, error) {
	var ps []model.PropPreset
	var total int64
	q := r.db.Where("(owner_id = ? OR is_preset = true)", ownerID)
	if category != "" && category != "all" {
		q = q.Where("category = ?", category)
	}
	if err := q.Model(&model.PropPreset{}).Count(&total).Error; err != nil {
		return nil, 0, err
	}
	err := q.Order("is_preset DESC, updated_at DESC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&ps).Error
	return ps, total, err
}
func (r *PropRepository) Update(p *model.PropPreset) error { return r.db.Save(p).Error }
func (r *PropRepository) Delete(id uuid.UUID) error {
	return r.db.Delete(&model.PropPreset{}, "id = ?", id).Error
}
