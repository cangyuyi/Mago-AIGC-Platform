package repository

import (
	"encoding/json"
	"fmt"
	"time"

	"mago-agent/api-gateway/internal/model"

	"gorm.io/gorm"
)

type ViralRepository struct {
	db *gorm.DB
}

func NewViralRepository(db *gorm.DB) *ViralRepository {
	return &ViralRepository{db: db}
}

// CreateViralVideo creates a new viral video record
func (r *ViralRepository) CreateViralVideo(v *model.ViralVideo) error {
	return r.db.Create(v).Error
}

// UpsertViralVideo creates or updates by platform+video_id
func (r *ViralRepository) UpsertViralVideo(v *model.ViralVideo) error {
	var existing model.ViralVideo
	result := r.db.Where("platform = ? AND video_id = ?", v.Platform, v.VideoID).First(&existing)
	if result.Error == gorm.ErrRecordNotFound {
		return r.db.Create(v).Error
	}
	if result.Error != nil {
		return result.Error
	}
	v.ID = existing.ID
	v.CreatedAt = existing.CreatedAt
	return r.db.Save(v).Error
}

// GetViralVideo retrieves a viral video by ID with shots preloaded
func (r *ViralRepository) GetViralVideo(id string) (*model.ViralVideo, error) {
	var v model.ViralVideo
	if err := r.db.Preload("Shots", func(db *gorm.DB) *gorm.DB {
		return db.Order("shot_index ASC")
	}).Where("id = ?", id).First(&v).Error; err != nil {
		return nil, err
	}
	return &v, nil
}

// ListViralVideos lists viral videos with filters
func (r *ViralRepository) ListViralVideos(platform, category, sortBy, order string, page, pageSize int) ([]model.ViralVideo, int64, error) {
	var videos []model.ViralVideo
	var total int64

	query := r.db.Model(&model.ViralVideo{})
	if platform != "" && platform != "all" {
		query = query.Where("platform = ?", platform)
	}
	if category != "" {
		query = query.Where("category = ?", category)
	}
	query = query.Where("analysis_status = ?", "completed")

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	allowedSorts := map[string]bool{
		"viral_score": true, "created_at": true, "analyzed_at": true,
		"duration": true, "title": true,
	}
	if !allowedSorts[sortBy] {
		sortBy = "viral_score"
	}
	if order != "asc" && order != "desc" {
		order = "desc"
	}
	orderClause := fmt.Sprintf("%s %s", sortBy, order)

	offset := (page - 1) * pageSize
	if err := query.Order(orderClause).Offset(offset).Limit(pageSize).Find(&videos).Error; err != nil {
		return nil, 0, err
	}
	return videos, total, nil
}

// UpdateAnalysisStatus updates the analysis status of a viral video
func (r *ViralRepository) UpdateAnalysisStatus(id string, status string, analysisErr string) error {
	updates := map[string]interface{}{
		"analysis_status": status,
	}
	if analysisErr != "" {
		updates["analysis_error"] = analysisErr
	}
	if status == "completed" {
		now := time.Now()
		updates["analyzed_at"] = &now
	}
	return r.db.Model(&model.ViralVideo{}).Where("id = ?", id).Updates(updates).Error
}

// UpdateViralVideoAnalysis updates the full analysis result
func (r *ViralRepository) UpdateViralVideoAnalysis(id string, updates map[string]interface{}) error {
	return r.db.Model(&model.ViralVideo{}).Where("id = ?", id).Updates(updates).Error
}

// SearchViralVideos performs keyword search on viral videos
func (r *ViralRepository) SearchViralVideos(keyword string, page, pageSize int) ([]model.ViralVideo, int64, error) {
	var videos []model.ViralVideo
	var total int64

	tagJSON, err := json.Marshal([]string{keyword})
	if err != nil {
		return nil, 0, err
	}
	query := r.db.Model(&model.ViralVideo{}).Where(
		"analysis_status = ? AND (title ILIKE ? OR description ILIKE ? OR tags @> ?::jsonb)",
		"completed", "%"+keyword+"%", "%"+keyword+"%", string(tagJSON),
	)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := query.Order("viral_score DESC").Offset(offset).Limit(pageSize).Find(&videos).Error; err != nil {
		return nil, 0, err
	}
	return videos, total, nil
}

// GetPendingAnalysis returns videos pending analysis (for workers)
func (r *ViralRepository) GetPendingAnalysis(limit int) ([]model.ViralVideo, error) {
	var videos []model.ViralVideo
	if err := r.db.Where("analysis_status = ?", "pending").
		Order("created_at ASC").Limit(limit).Find(&videos).Error; err != nil {
		return nil, err
	}
	return videos, nil
}

// CreateShots batch creates shots for a video
func (r *ViralRepository) CreateShots(shots []model.VideoShot) error {
	return r.db.CreateInBatches(shots, 100).Error
}

// GetShotsByVideoID returns all shots for a video
func (r *ViralRepository) GetShotsByVideoID(videoID string) ([]model.VideoShot, error) {
	var shots []model.VideoShot
	if err := r.db.Where("viral_video_id = ?", videoID).Order("shot_index ASC").Find(&shots).Error; err != nil {
		return nil, err
	}
	return shots, nil
}

// DeleteShotsByVideoID deletes all shots for a video (for re-analysis)
func (r *ViralRepository) DeleteShotsByVideoID(videoID string) error {
	return r.db.Where("viral_video_id = ?", videoID).Delete(&model.VideoShot{}).Error
}
