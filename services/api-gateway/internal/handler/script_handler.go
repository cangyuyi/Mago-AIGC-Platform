package handler

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/service"
)

type ScriptHandler struct {
	svc *service.ScriptService
}

func NewScriptHandler(svc *service.ScriptService) *ScriptHandler {
	return &ScriptHandler{svc: svc}
}

func (h *ScriptHandler) List(c *gin.Context) {
	projectIDStr := c.Query("project_id")
	if projectIDStr == "" {
		response.BadRequest(c, "project_id is required")
		return
	}
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		response.BadRequest(c, "invalid project_id")
		return
	}
	scripts, err := h.svc.ListByProjectOwned(projectID, MustGetUserID(c))
	if err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, scripts)
}

func (h *ScriptHandler) Create(c *gin.Context) {
	var script model.Script
	if err := c.ShouldBindJSON(&script); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	if script.ID == uuid.Nil {
		script.ID = uuid.New()
	}
	if err := h.svc.CreateOwned(&script, MustGetUserID(c)); err != nil {
		resourceError(c, err, "project not found")
		return
	}
	c.JSON(http.StatusCreated, script)
}

func (h *ScriptHandler) GetByID(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid script id")
		return
	}
	script, err := h.svc.GetByIDOwned(id, MustGetUserID(c))
	if err != nil {
		response.NotFound(c, "script not found")
		return
	}
	response.Success(c, script)
}

func (h *ScriptHandler) Update(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid script id")
		return
	}
	var script model.Script
	if err := c.ShouldBindJSON(&script); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	script.ID = id
	if err := h.svc.UpdateOwned(&script, MustGetUserID(c)); err != nil {
		resourceError(c, err, "script not found")
		return
	}
	response.Success(c, script)
}

func (h *ScriptHandler) Delete(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid script id")
		return
	}
	if err := h.svc.DeleteOwned(id, MustGetUserID(c)); err != nil {
		resourceError(c, err, "script not found")
		return
	}
	response.Success(c, gin.H{"deleted": true})
}

// Storyboard handlers

func (h *ScriptHandler) ListStoryboards(c *gin.Context) {
	projectIDStr := c.Query("project_id")
	if projectIDStr == "" {
		response.BadRequest(c, "project_id is required")
		return
	}
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		response.BadRequest(c, "invalid project_id")
		return
	}
	sbs, err := h.svc.ListStoryboardsByProjectOwned(projectID, MustGetUserID(c))
	if err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, sbs)
}

func (h *ScriptHandler) CreateStoryboard(c *gin.Context) {
	var sb model.Storyboard
	if err := c.ShouldBindJSON(&sb); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	if sb.ID == uuid.Nil {
		sb.ID = uuid.New()
	}
	if err := h.svc.CreateStoryboardOwned(&sb, MustGetUserID(c)); err != nil {
		resourceError(c, err, "project or script not found")
		return
	}
	c.JSON(http.StatusCreated, sb)
}

func (h *ScriptHandler) GetStoryboard(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid storyboard id")
		return
	}
	sb, err := h.svc.GetStoryboardOwned(id, MustGetUserID(c))
	if err != nil {
		response.NotFound(c, "storyboard not found")
		return
	}
	shots, err := h.svc.GetStoryboardShotsOwned(id, MustGetUserID(c))
	if err != nil {
		response.InternalError(c, "failed to load storyboard shots")
		return
	}
	response.Success(c, gin.H{"storyboard": sb, "shots": shots})
}

// ReplaceShots stores the full shot list of a storyboard.
// PUT /api/v1/storyboards/:id/shots  {"shots": [...]}
func (h *ScriptHandler) ReplaceShots(c *gin.Context) {
	userID, ok := UserID(c)
	if !ok {
		response.Unauthorized(c, "user not authenticated")
		return
	}
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid storyboard id")
		return
	}
	var body struct {
		Shots []model.StoryboardShot `json:"shots"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	shots, err := h.svc.ReplaceShotsOwned(id, userID, body.Shots)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrNoShots), errors.Is(err, service.ErrTooManyShots):
			response.BadRequest(c, err.Error())
		default:
			resourceError(c, err, "storyboard not found")
		}
		return
	}
	response.Success(c, gin.H{"storyboard_id": id, "count": len(shots), "shots": shots})
}
