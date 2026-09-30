package router

import (
	"mago-agent/api-gateway/internal/config"
	"mago-agent/api-gateway/internal/handler"
	"mago-agent/api-gateway/internal/middleware"
	"mago-agent/api-gateway/internal/pkg/jwt"

	"github.com/gin-gonic/gin"
)

func SetupRouter(
	cfg *config.Config,
	healthHandler *handler.HealthHandler,
	authHandler *handler.AuthHandler,
	projectHandler *handler.ProjectHandler,
	trendHandler *handler.TrendHandler,
	viralHandler *handler.ViralHandler,
	patternHandler *handler.PatternHandler,
	topicHandler *handler.TopicHandler,
	scriptHandler *handler.ScriptHandler,
	characterHandler *handler.CharacterHandler,
	styleHandler *handler.StyleHandler,
	assetHandler *handler.AssetHandler,
	promptHandler *handler.PromptHandler,
	jwtManager *jwt.Manager,
) *gin.Engine {
	r := gin.New()

	// --- Global middleware (order matters!) ---
	// 1. Recovery first (catch panics)
	r.Use(middleware.Recovery())
	// 2. Request ID for tracing
	r.Use(middleware.RequestID())
	// 3. Security headers
	r.Use(middleware.SecurityHeaders())
	// 4. Request size limit (10MB)
	r.Use(middleware.RequestSizeLimit(10 * 1024 * 1024))
	// 5. Logger
	r.Use(middleware.Logger())
	// 6. CORS
	r.Use(middleware.CORS(cfg.Server.AllowedOrigins))
	// 7. Global rate limit: 200 rps with burst of 50
	r.Use(middleware.GlobalRateLimiter(200, 50))

	// Health check (no auth)
	r.GET("/health", healthHandler.Health)
	r.GET("/api/v1/health", healthHandler.Health)

	// Metrics endpoint (for Prometheus)
	r.GET("/metrics", func(c *gin.Context) {
		c.String(200, "# HELP mago_api_up API server up\n# TYPE mago_api_up gauge\nmago_api_up 1\n")
	})

	// Auth routes (strict per-IP rate limit: 5 rps burst 10 to prevent brute force)
	auth := r.Group("/api/v1/auth")
	auth.Use(middleware.RateLimiter(5, 10))
	{
		auth.POST("/register", authHandler.Register)
		auth.POST("/login", authHandler.Login)
		auth.POST("/refresh", authHandler.Refresh)
	}

	// Authenticated API routes
	api := r.Group("/api/v1")
	api.Use(middleware.AuthMiddleware(jwtManager))
	// Per-IP rate limit for authenticated users: 50 rps burst 100
	api.Use(middleware.RateLimiter(50, 100))
	{
		api.GET("/auth/me", authHandler.Me)

		// Projects
		api.GET("/projects", projectHandler.List)
		api.POST("/projects", projectHandler.Create)
		api.GET("/projects/:id", projectHandler.Get)
		api.PUT("/projects/:id", projectHandler.Update)
		api.DELETE("/projects/:id", projectHandler.Delete)

		// Scripts & Storyboards (03)
		api.GET("/scripts", scriptHandler.List)
		api.POST("/scripts", scriptHandler.Create)
		api.GET("/scripts/:id", scriptHandler.GetByID)
		api.PUT("/scripts/:id", scriptHandler.Update)
		api.DELETE("/scripts/:id", scriptHandler.Delete)
		api.GET("/storyboards", scriptHandler.ListStoryboards)
		api.POST("/storyboards", scriptHandler.CreateStoryboard)
		api.GET("/storyboards/:id", scriptHandler.GetStoryboard)
		api.PUT("/storyboards/:id/shots", scriptHandler.ReplaceShots)

		// Characters (04)
		api.GET("/characters", characterHandler.List)
		api.POST("/characters", characterHandler.Create)
		api.GET("/characters/:id", characterHandler.GetByID)
		api.PUT("/characters/:id", characterHandler.Update)
		api.DELETE("/characters/:id", characterHandler.Delete)
		api.GET("/characters/:id/images", characterHandler.ListImages)
		api.POST("/characters/:id/images", characterHandler.AddImage)
		api.DELETE("/characters/images/:imageId", characterHandler.DeleteImage)

		// Style Presets (04)
		api.GET("/styles", styleHandler.List)
		api.GET("/styles/categories", styleHandler.Categories)
		api.POST("/styles", styleHandler.Create)
		api.GET("/styles/:id", styleHandler.GetByID)
		api.PUT("/styles/:id", styleHandler.Update)
		api.DELETE("/styles/:id", styleHandler.Delete)

		// Assets - Scenes & Props (04)
		api.GET("/scenes", assetHandler.ListScenes)
		api.POST("/scenes", assetHandler.CreateScene)
		api.GET("/props", assetHandler.ListProps)
		api.POST("/props", assetHandler.CreateProp)

		// Prompt Packages (05)
		api.GET("/prompt-packages", promptHandler.List)
		api.POST("/prompt-packages", promptHandler.Create)
		api.GET("/prompt-packages/:id", promptHandler.Get)
		api.POST("/prompt-packages/:id/prompts", promptHandler.AddPrompts)
		api.DELETE("/prompt-packages/:id", promptHandler.Delete)

		// Trends (02)
		api.GET("/trends", trendHandler.List)
		api.GET("/trends/rising", trendHandler.GetRising)
		api.GET("/trends/:id", trendHandler.GetByID)
		api.POST("/trends/crawl-now", middleware.RequireRoles("owner", "admin"), trendHandler.CrawlNow)
		api.GET("/trends/task/:task_id", trendHandler.TaskStatus)
		api.GET("/trends/crawl-tasks", trendHandler.ListCrawlTasks)

		// Viral Videos (02)
		api.GET("/viral-videos", viralHandler.List)
		api.GET("/viral-videos/search", viralHandler.Search)
		api.POST("/viral-videos/analyze", viralHandler.Analyze)
		api.GET("/viral-videos/analyze/:task_id", viralHandler.AnalyzeStatus)
		api.GET("/viral-videos/:id", viralHandler.GetByID)

		// Viral Patterns (02)
		api.GET("/viral-patterns", patternHandler.List)
		api.GET("/viral-patterns/:id", patternHandler.GetByID)
		api.POST("/viral-patterns", middleware.RequireRoles("owner", "admin"), patternHandler.Create)

		// Topic Recommendations (02)
		api.POST("/topic-recommendations", topicHandler.Recommend)
		api.GET("/topic-recommendations", topicHandler.List)
	}
	return r
}
