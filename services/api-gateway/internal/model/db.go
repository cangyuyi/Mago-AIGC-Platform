package model

import (
	"fmt"

	"mago-agent/api-gateway/internal/config"

	"go.uber.org/zap"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

func InitDB(cfg *config.DatabaseConfig) (*gorm.DB, error) {
	db, err := gorm.Open(postgres.Open(cfg.DSN()), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Warn),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect database: %w", err)
	}

	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get sql.DB: %w", err)
	}
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)

	// Auto-migrate core tables (for MVP; migrations should be used in production)
	if err := db.AutoMigrate(
		&User{},
		&Organization{},
		&Membership{},
		&Project{},
		&Script{},
		&Storyboard{},
		&StoryboardShot{},
		&Character{},
		&StylePreset{},
		&TrendTopic{},
		&ViralVideo{},
		&CreativeSession{},
		&VideoShot{},
		&ViralPattern{},
		&CrawlTask{},
		&TopicRecommendation{},
		// Extended schema models. Keeping these in AutoMigrate makes a fresh
		// development database usable even when the SQL migrations have not
		// been run manually (the production compose file runs them first).
		&CharacterRefImage{},
		&StyleCombination{},
		&ScenePreset{},
		&PropPreset{},
		&BrandKit{},
		&PromptPackage{},
		&Prompt{},
		&ModelConfig{},
	); err != nil {
		return nil, fmt.Errorf("auto-migrate failed: %w", err)
	}

	zap.L().Info("Database connected and migrated successfully")
	DB = db
	return db, nil
}
