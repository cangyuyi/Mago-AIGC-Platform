package repository

import (
	"fmt"

	"mago-agent/api-gateway/internal/model"

	"gorm.io/gorm"
)

type PatternRepository struct {
	db *gorm.DB
}

func NewPatternRepository(db *gorm.DB) *PatternRepository {
	return &PatternRepository{db: db}
}

func (r *PatternRepository) Create(p *model.ViralPattern) error {
	return r.db.Create(p).Error
}

func (r *PatternRepository) GetByID(id string) (*model.ViralPattern, error) {
	var p model.ViralPattern
	if err := r.db.Where("id = ?", id).First(&p).Error; err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *PatternRepository) List(patternType, category string, verifiedOnly bool, page, pageSize int) ([]model.ViralPattern, int64, error) {
	var patterns []model.ViralPattern
	var total int64

	query := r.db.Model(&model.ViralPattern{})
	if patternType != "" && patternType != "all" {
		query = query.Where("pattern_type = ?", patternType)
	}
	if category != "" {
		query = query.Where("category = ?", category)
	}
	if verifiedOnly {
		query = query.Where("is_verified = ?", true)
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := query.Order("avg_viral_score DESC, sample_count DESC").
		Offset(offset).Limit(pageSize).Find(&patterns).Error; err != nil {
		return nil, 0, err
	}
	return patterns, total, nil
}

// FindSimilarByName finds patterns with similar name (dedup check)
func (r *PatternRepository) FindSimilarByName(name string, patternType string) (*model.ViralPattern, error) {
	var p model.ViralPattern
	result := r.db.Where("pattern_type = ? AND name ILIKE ?", patternType, fmt.Sprintf("%%%s%%", name)).First(&p)
	if result.Error == gorm.ErrRecordNotFound {
		return nil, nil
	}
	if result.Error != nil {
		return nil, result.Error
	}
	return &p, nil
}

// UpdateStats updates sample count and avg viral score
func (r *PatternRepository) UpdateStats(id string, avgScore float64, count int) error {
	return r.db.Model(&model.ViralPattern{}).Where("id = ?", id).
		Updates(map[string]interface{}{
			"avg_viral_score": avgScore,
			"sample_count":    count,
		}).Error
}
