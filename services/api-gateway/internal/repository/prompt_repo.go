package repository

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
	"mago-agent/api-gateway/internal/model"
)

type PromptRepository struct{ db *gorm.DB }

func NewPromptRepository(db *gorm.DB) *PromptRepository                { return &PromptRepository{db: db} }
func (r *PromptRepository) CreatePackage(p *model.PromptPackage) error { return r.db.Create(p).Error }
func (r *PromptRepository) GetPackage(id uuid.UUID) (*model.PromptPackage, error) {
	var p model.PromptPackage
	err := r.db.Where("id=?", id).First(&p).Error
	return &p, err
}
func (r *PromptRepository) ListPackages(projectID uuid.UUID) ([]model.PromptPackage, error) {
	var ps []model.PromptPackage
	err := r.db.Where("project_id=?", projectID).Order("created_at DESC").Find(&ps).Error
	return ps, err
}
func (r *PromptRepository) CreatePrompt(p *model.Prompt) error    { return r.db.Create(p).Error }
func (r *PromptRepository) CreatePrompts(ps []model.Prompt) error { return r.db.Create(&ps).Error }
func (r *PromptRepository) ListPrompts(packageID uuid.UUID) ([]model.Prompt, error) {
	var ps []model.Prompt
	err := r.db.Where("package_id=?", packageID).Order("shot_id, model_id").Find(&ps).Error
	return ps, err
}
func (r *PromptRepository) UpdatePrompt(p *model.Prompt) error { return r.db.Save(p).Error }
func (r *PromptRepository) DeletePackage(id uuid.UUID) error {
	tx := r.db.Begin()
	if tx.Error != nil {
		return tx.Error
	}
	if err := tx.Where("package_id = ?", id).Delete(&model.Prompt{}).Error; err != nil {
		tx.Rollback()
		return err
	}
	if err := tx.Delete(&model.PromptPackage{}, "id = ?", id).Error; err != nil {
		tx.Rollback()
		return err
	}
	return tx.Commit().Error
}
