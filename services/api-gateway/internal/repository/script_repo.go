package repository

import (
	"mago-agent/api-gateway/internal/model"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ScriptRepository struct {
	db *gorm.DB
}

func NewScriptRepository(db *gorm.DB) *ScriptRepository {
	return &ScriptRepository{db: db}
}

func (r *ScriptRepository) Create(script *model.Script) error {
	return r.db.Create(script).Error
}

func (r *ScriptRepository) FindByID(id uuid.UUID) (*model.Script, error) {
	var s model.Script
	if err := r.db.Where("id = ?", id).First(&s).Error; err != nil {
		return nil, err
	}
	return &s, nil
}

func (r *ScriptRepository) ListByProject(projectID uuid.UUID) ([]model.Script, error) {
	var scripts []model.Script
	if err := r.db.Where("project_id = ?", projectID).
		Order("version DESC").
		Find(&scripts).Error; err != nil {
		return nil, err
	}
	return scripts, nil
}

func (r *ScriptRepository) Update(script *model.Script) error {
	return r.db.Save(script).Error
}

func (r *ScriptRepository) UpdateOwned(script *model.Script) error {
	var current model.Script
	if err := r.db.Where("id = ?", script.ID).First(&current).Error; err != nil {
		return err
	}
	return r.db.Model(&current).Updates(script).Error
}

func (r *ScriptRepository) Delete(id uuid.UUID) error {
	return r.db.Delete(&model.Script{}, "id = ?", id).Error
}
