package repository

import (
	"mago-agent/api-gateway/internal/model"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type TopicRepository struct {
	db *gorm.DB
}

func NewTopicRepository(db *gorm.DB) *TopicRepository {
	return &TopicRepository{db: db}
}

func (r *TopicRepository) Create(rec *model.TopicRecommendation) error {
	return r.db.Create(rec).Error
}

func (r *TopicRepository) GetByID(id string) (*model.TopicRecommendation, error) {
	var rec model.TopicRecommendation
	if err := r.db.Where("id = ?", id).First(&rec).Error; err != nil {
		return nil, err
	}
	return &rec, nil
}

func (r *TopicRepository) ListByUser(userID uuid.UUID, page, pageSize int) ([]model.TopicRecommendation, int64, error) {
	var recs []model.TopicRecommendation
	var total int64

	query := r.db.Model(&model.TopicRecommendation{}).Where("user_id = ?", userID)
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := query.Order("created_at DESC").Offset(offset).Limit(pageSize).Find(&recs).Error; err != nil {
		return nil, 0, err
	}
	return recs, total, nil
}
