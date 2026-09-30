package handler

import (
	"io"
	"net/http"
	"strconv"

	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/repository"

	"github.com/gin-gonic/gin"
)

type TrendHandler struct {
	trendRepo  *repository.TrendRepository
	crawlRepo  *repository.CrawlRepository
	agentProxy *AgentProxy
}

func NewTrendHandler(trendRepo *repository.TrendRepository, crawlRepo *repository.CrawlRepository, agentProxy *AgentProxy) *TrendHandler {
	return &TrendHandler{trendRepo: trendRepo, crawlRepo: crawlRepo, agentProxy: agentProxy}
}

// List returns paginated trend topics with filters
// GET /api/v1/trends?platform=douyin&category=entertainment&status=rising&page=1&page_size=20&sort=hot_value_growth&order=desc
func (h *TrendHandler) List(c *gin.Context) {
	platform := c.DefaultQuery("platform", "all")
	category := c.Query("category")
	status := c.Query("status")
	lifecycle := c.Query("lifecycle")
	sort := c.DefaultQuery("sort", "hot_value_growth")
	order := c.DefaultQuery("order", "desc")
	page, pageSize := response.GetPagination(c)

	topics, total, err := h.trendRepo.ListTrends(platform, category, status, lifecycle, sort, order, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, topics, total, page, pageSize)
}

// GetRising returns rapidly-rising trends (hot_value_growth > threshold)
// GET /api/v1/trends/rising?platform=all&limit=10
func (h *TrendHandler) GetRising(c *gin.Context) {
	platform := c.DefaultQuery("platform", "all")
	limit := 20
	if l := c.Query("limit"); l != "" {
		if n := parseInt(l); n > 0 && n <= 100 {
			limit = n
		}
	}
	topics, err := h.trendRepo.GetRisingTrends(platform, limit)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, topics)
}

// GetByID returns a single trend topic
// GET /api/v1/trends/:id
func (h *TrendHandler) GetByID(c *gin.Context) {
	id := c.Param("id")
	topic, err := h.trendRepo.GetByID(id)
	if err != nil {
		response.NotFound(c, "trend not found")
		return
	}
	response.Success(c, topic)
}

// CrawlNow triggers an immediate crawl (admin)
// POST /api/v1/trends/crawl-now
func (h *TrendHandler) CrawlNow(c *gin.Context) {
	// Accept both the documented JSON body and query parameters. The web client
	// submits JSON, while older integrations used query parameters; query values
	// intentionally win when both are present.
	var body struct {
		Platform string `json:"platform"`
		Category string `json:"category"`
	}
	if err := c.ShouldBindJSON(&body); err != nil && err != io.EOF {
		response.BadRequest(c, "invalid request: "+err.Error())
		return
	}

	platform := body.Platform
	if queryPlatform := c.Query("platform"); queryPlatform != "" {
		platform = queryPlatform
	}
	category := body.Category
	if queryCategory := c.Query("category"); queryCategory != "" {
		category = queryCategory
	}

	payload := gin.H{}
	if platform != "" && platform != "all" {
		payload["platform"] = platform
	}
	if category != "" {
		payload["category"] = category
	}
	h.agentProxy.ForwardJSON(c, http.MethodPost, "/trends/crawl-now", payload)
}

// TaskStatus returns the live status of an Agent crawl task.
// GET /api/v1/trends/task/:task_id
func (h *TrendHandler) TaskStatus(c *gin.Context) {
	h.agentProxy.Forward(c, http.MethodGet, "/trends/task/"+c.Param("task_id"))
}

// ListCrawlTasks returns crawl task history
// GET /api/v1/trends/crawl-tasks
func (h *TrendHandler) ListCrawlTasks(c *gin.Context) {
	platform := c.DefaultQuery("platform", "all")
	status := c.Query("status")
	taskType := c.Query("task_type")
	page, pageSize := response.GetPagination(c)

	tasks, total, err := h.crawlRepo.List(platform, status, taskType, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, tasks, total, page, pageSize)
}

func parseInt(s string) int {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}
