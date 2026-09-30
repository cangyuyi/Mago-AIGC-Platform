package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/service"
)

type PromptHandler struct{ svc *service.PromptService }

func NewPromptHandler(svc *service.PromptService) *PromptHandler { return &PromptHandler{svc: svc} }

func (h *PromptHandler) List(c *gin.Context) {
	projectID, err := uuid.Parse(c.Query("project_id"))
	if err != nil {
		response.BadRequest(c, "valid project_id is required")
		return
	}
	pkgs, err := h.svc.ListPackagesOwned(projectID, MustGetUserID(c))
	if err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, pkgs)
}
func (h *PromptHandler) Create(c *gin.Context) {
	var pkg model.PromptPackage
	if err := c.ShouldBindJSON(&pkg); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	if err := h.svc.CreatePackageOwned(&pkg, MustGetUserID(c)); err != nil {
		resourceError(c, err, "project or storyboard not found")
		return
	}
	c.JSON(http.StatusCreated, pkg)
}
func (h *PromptHandler) Get(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	pkg, err := h.svc.GetPackageOwned(id, MustGetUserID(c))
	if err != nil {
		response.NotFound(c, "package not found")
		return
	}
	prompts, err := h.svc.ListPromptsOwned(id, MustGetUserID(c))
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, gin.H{"package": pkg, "prompts": prompts})
}
func (h *PromptHandler) AddPrompts(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	var req struct {
		Prompts []model.Prompt `json:"prompts"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	if err := h.svc.CreatePromptsOwned(id, MustGetUserID(c), req.Prompts); err != nil {
		resourceError(c, err, "package or shot not found")
		return
	}
	response.Success(c, gin.H{"created": len(req.Prompts)})
}
func (h *PromptHandler) Delete(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	if err := h.svc.DeletePackageOwned(id, MustGetUserID(c)); err != nil {
		resourceError(c, err, "package not found")
		return
	}
	response.Success(c, gin.H{"deleted": true})
}
