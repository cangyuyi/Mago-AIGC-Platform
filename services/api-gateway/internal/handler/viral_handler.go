package handler

import (
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/repository"

	"net/http"

	"github.com/gin-gonic/gin"
)

type ViralHandler struct {
	viralRepo  *repository.ViralRepository
	agentProxy *AgentProxy
}

func NewViralHandler(viralRepo *repository.ViralRepository, agentProxy *AgentProxy) *ViralHandler {
	return &ViralHandler{viralRepo: viralRepo, agentProxy: agentProxy}
}

// List returns paginated viral videos
// GET /api/v1/viral-videos?platform=douyin&category=beauty&sort=viral_score&order=desc&page=1&page_size=20
func (h *ViralHandler) List(c *gin.Context) {
	platform := c.DefaultQuery("platform", "all")
	category := c.Query("category")
	sort := c.DefaultQuery("sort", "viral_score")
	order := c.DefaultQuery("order", "desc")
	page, pageSize := response.GetPagination(c)

	videos, total, err := h.viralRepo.ListViralVideos(platform, category, sort, order, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, videos, total, page, pageSize)
}

// GetByID returns a viral video with full analysis
// GET /api/v1/viral-videos/:id
func (h *ViralHandler) GetByID(c *gin.Context) {
	id := c.Param("id")
	video, err := h.viralRepo.GetViralVideo(id)
	if err != nil {
		response.NotFound(c, "viral video not found")
		return
	}
	response.Success(c, video)
}

// Analyze submits a video URL for analysis (async)
// POST /api/v1/viral-videos/analyze {url, platform}
func (h *ViralHandler) Analyze(c *gin.Context) {
	var req struct {
		URL             string `json:"url" binding:"required,url"`
		Platform        string `json:"platform,omitempty"`
		Category        string `json:"category,omitempty"`
		AnalysisMode    string `json:"analysis_mode,omitempty"`
		ExtractPatterns *bool  `json:"extract_patterns,omitempty"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	h.agentProxy.ForwardJSON(c, http.MethodPost, "/viral-videos/analyze", req)
}

// AnalyzeStatus returns task status
// GET /api/v1/viral-videos/analyze/:task_id
func (h *ViralHandler) AnalyzeStatus(c *gin.Context) {
	taskID := c.Param("task_id")
	h.agentProxy.Forward(c, http.MethodGet, "/viral-videos/analyze/"+taskID)
}

// Search searches viral videos by keyword
// GET /api/v1/viral-videos/search?q=beauty&page=1&page_size=20
func (h *ViralHandler) Search(c *gin.Context) {
	q := c.Query("q")
	if q == "" {
		response.BadRequest(c, "search query 'q' is required")
		return
	}
	page, pageSize := response.GetPagination(c)

	videos, total, err := h.viralRepo.SearchViralVideos(q, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, videos, total, page, pageSize)
}
