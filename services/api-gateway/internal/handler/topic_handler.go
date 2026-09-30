package handler

import (
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/repository"

	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type TopicHandler struct {
	topicRepo  *repository.TopicRepository
	agentProxy *AgentProxy
}

func NewTopicHandler(topicRepo *repository.TopicRepository, agentProxy *AgentProxy) *TopicHandler {
	return &TopicHandler{topicRepo: topicRepo, agentProxy: agentProxy}
}

// Recommend generates topic recommendations
// POST /api/v1/topic-recommendations {"category":"beauty","keywords":[],"reference_video_urls":[],"count":10}
func (h *TopicHandler) Recommend(c *gin.Context) {
	var req struct {
		Category           string   `json:"category,omitempty"`
		Keywords           []string `json:"keywords,omitempty"`
		ReferenceVideoURLs []string `json:"reference_video_urls,omitempty"`
		Count              int      `json:"count"`
		TargetPlatform     string   `json:"target_platform,omitempty"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	if req.Count <= 0 {
		req.Count = 10
	}
	if req.Count > 30 {
		req.Count = 30
	}

	h.agentProxy.ForwardJSON(c, http.MethodPost, "/topic-recommendations/generate", req)
}

// List returns user's topic recommendation history
// GET /api/v1/topic-recommendations
func (h *TopicHandler) List(c *gin.Context) {
	page, pageSize := response.GetPagination(c)
	userID := MustGetUserID(c)
	if userID == uuid.Nil {
		return
	}
	recommendations, total, err := h.topicRepo.ListByUser(userID, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, recommendations, total, page, pageSize)
}
