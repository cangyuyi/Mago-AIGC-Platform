package repository

import (
	"fmt"

	"mago-agent/api-gateway/internal/model"

	"gorm.io/gorm"
)

type TrendRepository struct {
	db *gorm.DB
}

func NewTrendRepository(db *gorm.DB) *TrendRepository {
	return &TrendRepository{db: db}
}

func (r *TrendRepository) CreateTrend(topic *model.TrendTopic) error {
	return r.db.Create(topic).Error
}

// ListTrends lists trends with comprehensive filtering
func (r *TrendRepository) ListTrends(platform, category, status, lifecycle, sortBy, order string, page, pageSize int) ([]model.TrendTopic, int64, error) {
	var topics []model.TrendTopic
	var total int64

	query := r.db.Model(&model.TrendTopic{})
	if platform != "" && platform != "all" {
		query = query.Where("platform = ?", platform)
	}
	if category != "" {
		query = query.Where("category = ?", category)
	}
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if lifecycle != "" {
		query = query.Where("lifecycle_stage = ?", lifecycle)
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	// Validate sort field
	allowedSorts := map[string]bool{"hot_value": true, "hot_value_growth": true, "rank_position": true, "created_at": true, "last_updated_at": true}
	if !allowedSorts[sortBy] {
		sortBy = "hot_value_growth"
	}
	if order != "asc" && order != "desc" {
		order = "desc"
	}
	orderClause := fmt.Sprintf("%s %s", sortBy, order)

	offset := (page - 1) * pageSize
	if err := query.Order(orderClause).
		Offset(offset).Limit(pageSize).Find(&topics).Error; err != nil {
		return nil, 0, err
	}
	return topics, total, nil
}

func (r *TrendRepository) UpsertTrend(topic *model.TrendTopic) error {
	var existing model.TrendTopic
	result := r.db.Where("platform = ? AND (topic_id = ? OR title = ?)",
		topic.Platform, topic.TopicID, topic.Title).First(&existing)
	if result.Error == gorm.ErrRecordNotFound {
		return r.db.Create(topic).Error
	}
	if result.Error != nil {
		return result.Error
	}
	topic.ID = existing.ID
	topic.CreatedAt = existing.CreatedAt
	return r.db.Save(topic).Error
}

func (r *TrendRepository) GetByID(id string) (*model.TrendTopic, error) {
	var topic model.TrendTopic
	if err := r.db.Where("id = ?", id).First(&topic).Error; err != nil {
		return nil, err
	}
	return &topic, nil
}

// GetRisingTrends returns topics with highest hot_value_growth
func (r *TrendRepository) GetRisingTrends(platform string, limit int) ([]model.TrendTopic, error) {
	var topics []model.TrendTopic
	query := r.db.Model(&model.TrendTopic{}).
		Where("status = 'rising' AND hot_value_growth > 0")
	if platform != "" && platform != "all" {
		query = query.Where("platform = ?", platform)
	}
	if err := query.Order("hot_value_growth DESC").Limit(limit).Find(&topics).Error; err != nil {
		return nil, err
	}
	return topics, nil
}

// BatchUpsert creates or updates multiple trends
func (r *TrendRepository) BatchUpsert(topics []model.TrendTopic) (created int, updated int, err error) {
	for _, t := range topics {
		var existing model.TrendTopic
		result := r.db.Where("platform = ? AND (topic_id = ? OR title = ?)",
			t.Platform, t.TopicID, t.Title).First(&existing)
		if result.Error == gorm.ErrRecordNotFound {
			if e := r.db.Create(&t).Error; e != nil {
				err = e
				return
			}
			created++
		} else if result.Error == nil {
			t.ID = existing.ID
			t.CreatedAt = existing.CreatedAt
			if e := r.db.Save(&t).Error; e != nil {
				err = e
				return
			}
			updated++
		}
	}
	return
}
