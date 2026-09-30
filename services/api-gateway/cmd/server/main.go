package main

import (
	"net/http"
	"time"

	"mago-agent/api-gateway/internal/config"
	"mago-agent/api-gateway/internal/handler"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/pkg/jwt"
	"mago-agent/api-gateway/internal/pkg/logger"
	"mago-agent/api-gateway/internal/repository"
	"mago-agent/api-gateway/internal/router"
	"mago-agent/api-gateway/internal/service"

	"go.uber.org/zap"
)

func main() {
	cfg := config.MustLoad()
	logger.Init(cfg.Server.Env)
	defer logger.Sync()
	log := logger.L
	log.Info("Starting Mago Agent API Gateway", zap.String("version", cfg.App.Version))

	db, err := model.InitDB(&cfg.Database)
	if err != nil {
		log.Fatal("DB init failed", zap.Error(err))
	}
	jwtManager := jwt.NewManager(cfg.JWT.Secret, cfg.JWT.AccessTTLMin, cfg.JWT.RefreshTTLDays)

	// Repositories
	userRepo := repository.NewUserRepository(db)
	projectRepo := repository.NewProjectRepository(db)
	trendRepo := repository.NewTrendRepository(db)
	viralRepo := repository.NewViralRepository(db)
	patternRepo := repository.NewPatternRepository(db)
	crawlRepo := repository.NewCrawlRepository(db)
	topicRepo := repository.NewTopicRepository(db)
	scriptRepo := repository.NewScriptRepository(db)
	storyboardRepo := repository.NewStoryboardRepository(db)
	characterRepo := repository.NewCharacterRepository(db)
	styleRepo := repository.NewStyleRepository(db)
	sceneRepo := repository.NewSceneRepository(db)
	propRepo := repository.NewPropRepository(db)
	promptRepo := repository.NewPromptRepository(db)

	// Services
	authService := service.NewAuthService(userRepo, jwtManager)
	projectService := service.NewProjectService(projectRepo)
	scriptService := service.NewScriptService(scriptRepo, storyboardRepo, projectRepo)
	characterService := service.NewCharacterService(characterRepo)
	styleService := service.NewStyleService(styleRepo)
	sceneService := service.NewSceneService(sceneRepo)
	propService := service.NewPropService(propRepo)
	promptService := service.NewPromptService(promptRepo, projectRepo, storyboardRepo)

	// Handlers
	agentProxy := handler.NewAgentProxy(cfg.Agent.BaseURL)
	healthHandler := handler.NewHealthHandler(cfg)
	authHandler := handler.NewAuthHandler(authService)
	projectHandler := handler.NewProjectHandler(projectService)
	trendHandler := handler.NewTrendHandler(trendRepo, crawlRepo, agentProxy)
	viralHandler := handler.NewViralHandler(viralRepo, agentProxy)
	patternHandler := handler.NewPatternHandler(patternRepo)
	topicHandler := handler.NewTopicHandler(topicRepo, agentProxy)
	scriptHandler := handler.NewScriptHandler(scriptService)
	characterHandler := handler.NewCharacterHandler(characterService)
	styleHandler := handler.NewStyleHandler(styleService)
	assetHandler := handler.NewAssetHandler(sceneService, propService)
	promptHandler := handler.NewPromptHandler(promptService)

	r := router.SetupRouter(cfg, healthHandler, authHandler, projectHandler,
		trendHandler, viralHandler, patternHandler, topicHandler,
		scriptHandler, characterHandler, styleHandler, assetHandler, promptHandler, jwtManager)

	log.Info("API Gateway listening on :" + cfg.Server.Port)
	srv := &http.Server{Addr: ":" + cfg.Server.Port, Handler: r,
		ReadTimeout: 30 * time.Second, WriteTimeout: 120 * time.Second, IdleTimeout: 120 * time.Second}
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal("Server failed", zap.Error(err))
	}
}
