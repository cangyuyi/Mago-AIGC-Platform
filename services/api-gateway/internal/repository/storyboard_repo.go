package repository

import (
	"mago-agent/api-gateway/internal/model"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type StoryboardRepository struct {
	db *gorm.DB
}

func NewStoryboardRepository(db *gorm.DB) *StoryboardRepository {
	return &StoryboardRepository{db: db}
}

func (r *StoryboardRepository) Create(sb *model.Storyboard) error {
	return r.db.Create(sb).Error
}

func (r *StoryboardRepository) FindByID(id uuid.UUID) (*model.Storyboard, error) {
	var sb model.Storyboard
	if err := r.db.Where("id = ?", id).First(&sb).Error; err != nil {
		return nil, err
	}
	return &sb, nil
}

func (r *StoryboardRepository) GetShots(storyboardID uuid.UUID) ([]model.StoryboardShot, error) {
	var shots []model.StoryboardShot
	if err := r.db.Where("storyboard_id = ?", storyboardID).Order("shot_index ASC").Find(&shots).Error; err != nil {
		return nil, err
	}
	return shots, nil
}

func (r *StoryboardRepository) CreateShot(shot *model.StoryboardShot) error {
	return r.db.Create(shot).Error
}

func (r *StoryboardRepository) UpdateShot(shot *model.StoryboardShot) error {
	return r.db.Save(shot).Error
}

func (r *StoryboardRepository) DeleteShot(id uuid.UUID) error {
	return r.db.Delete(&model.StoryboardShot{}, "id = ?", id).Error
}

func (r *StoryboardRepository) ListByProject(projectID uuid.UUID) ([]model.Storyboard, error) {
	var sbs []model.Storyboard
	if err := r.db.Where("project_id = ?", projectID).Order("version DESC").Find(&sbs).Error; err != nil {
		return nil, err
	}
	return sbs, nil
}

// ReplaceShots atomically removes every existing shot of a storyboard and
// inserts the given ones. Using a transaction guarantees that a failed insert
// can never leave a storyboard with a half-written shot list.
func (r *StoryboardRepository) ReplaceShots(storyboardID uuid.UUID, shots []model.StoryboardShot) ([]model.StoryboardShot, error) {
	err := r.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("storyboard_id = ?", storyboardID).Delete(&model.StoryboardShot{}).Error; err != nil {
			return err
		}
		if len(shots) == 0 {
			return nil
		}
		return tx.Create(&shots).Error
	})
	if err != nil {
		return nil, err
	}
	var saved []model.StoryboardShot
	if err := r.db.Where("storyboard_id = ?", storyboardID).Order("shot_index ASC").Find(&saved).Error; err != nil {
		return nil, err
	}
	return saved, nil
}
