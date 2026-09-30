package handler

import (
	"net/http"

	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/repository"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type PatternHandler struct{ patternRepo *repository.PatternRepository }

func NewPatternHandler(patternRepo *repository.PatternRepository) *PatternHandler {
	return &PatternHandler{patternRepo: patternRepo}
}

func (h *PatternHandler) List(c *gin.Context) {
	patternType := c.DefaultQuery("type", "all")
	category := c.Query("category")
	verified := c.DefaultQuery("verified", "false") == "true"
	page, pageSize := response.GetPagination(c)
	patterns, total, err := h.patternRepo.List(patternType, category, verified, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, patterns, total, page, pageSize)
}

func (h *PatternHandler) GetByID(c *gin.Context) {
	pattern, err := h.patternRepo.GetByID(c.Param("id"))
	if err != nil {
		response.NotFound(c, "pattern not found")
		return
	}
	response.Success(c, pattern)
}

// Create adds a pattern. Production deployments should put this route behind an admin role check.
func (h *PatternHandler) Create(c *gin.Context) {
	var pattern model.ViralPattern
	if err := c.ShouldBindJSON(&pattern); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	if pattern.Name == "" || pattern.PatternType == "" || pattern.Description == "" {
		response.BadRequest(c, "name, pattern_type and description are required")
		return
	}
	// Never trust a client-supplied primary key for an admin-created shared resource.
	pattern.ID = uuid.New()
	pattern.IsVerified = false
	if err := h.patternRepo.Create(&pattern); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusCreated, pattern)
}
