package repository

import (
	"mago-agent/api-gateway/internal/model"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ProjectRepository struct {
	db *gorm.DB
}

func NewProjectRepository(db *gorm.DB) *ProjectRepository {
	return &ProjectRepository{db: db}
}

func (r *ProjectRepository) Create(project *model.Project) error {
	return r.db.Create(project).Error
}

func (r *ProjectRepository) FindByID(id uuid.UUID) (*model.Project, error) {
	var p model.Project
	if err := r.db.Where("id = ?", id).First(&p).Error; err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *ProjectRepository) ListByOwner(ownerID uuid.UUID, page, pageSize int) ([]model.Project, int64, error) {
	var projects []model.Project
	var total int64

	if err := r.db.Model(&model.Project{}).Where("owner_id = ?", ownerID).Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := r.db.Where("owner_id = ?", ownerID).
		Order("updated_at DESC").
		Offset(offset).Limit(pageSize).
		Find(&projects).Error; err != nil {
		return nil, 0, err
	}
	return projects, total, nil
}

func (r *ProjectRepository) Update(project *model.Project) error {
	return r.db.Save(project).Error
}

func (r *ProjectRepository) Delete(id uuid.UUID) error {
	return r.db.Delete(&model.Project{}, "id = ?", id).Error
}
