package repository

import (
	"mago-agent/api-gateway/internal/model"

	"gorm.io/gorm"
)

type CrawlRepository struct {
	db *gorm.DB
}

func NewCrawlRepository(db *gorm.DB) *CrawlRepository {
	return &CrawlRepository{db: db}
}

func (r *CrawlRepository) Create(task *model.CrawlTask) error {
	return r.db.Create(task).Error
}

func (r *CrawlRepository) Update(task *model.CrawlTask) error {
	return r.db.Save(task).Error
}

func (r *CrawlRepository) GetByID(id string) (*model.CrawlTask, error) {
	var task model.CrawlTask
	if err := r.db.Where("id = ?", id).First(&task).Error; err != nil {
		return nil, err
	}
	return &task, nil
}

func (r *CrawlRepository) List(platform, status, taskType string, page, pageSize int) ([]model.CrawlTask, int64, error) {
	var tasks []model.CrawlTask
	var total int64

	query := r.db.Model(&model.CrawlTask{})
	if platform != "" && platform != "all" {
		query = query.Where("platform = ?", platform)
	}
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if taskType != "" {
		query = query.Where("task_type = ?", taskType)
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := query.Order("created_at DESC").Offset(offset).Limit(pageSize).Find(&tasks).Error; err != nil {
		return nil, 0, err
	}
	return tasks, total, nil
}

// GetLatestByPlatform returns the most recent crawl task for a platform+type
func (r *CrawlRepository) GetLatestByPlatform(platform, taskType string) (*model.CrawlTask, error) {
	var task model.CrawlTask
	result := r.db.Where("platform = ? AND task_type = ?", platform, taskType).
		Order("created_at DESC").First(&task)
	if result.Error == gorm.ErrRecordNotFound {
		return nil, nil
	}
	if result.Error != nil {
		return nil, result.Error
	}
	return &task, nil
}
