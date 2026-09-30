package handler

import (
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/service"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type ProjectHandler struct {
	projectService *service.ProjectService
}

func NewProjectHandler(projectService *service.ProjectService) *ProjectHandler {
	return &ProjectHandler{projectService: projectService}
}

func (h *ProjectHandler) Create(c *gin.Context) {
	userID := MustGetUserID(c)
	var input service.CreateProjectInput
	if err := c.ShouldBindJSON(&input); err != nil {
		response.BadRequest(c, "invalid request: "+err.Error())
		return
	}
	// Get orgID from context if available
	var orgID *uuid.UUID
	if oid, exists := c.Get("org_id"); exists {
		if id, ok := oid.(uuid.UUID); ok {
			orgID = &id
		}
	}
	project, err := h.projectService.Create(userID, orgID, &input)
	if err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, project)
}

func (h *ProjectHandler) List(c *gin.Context) {
	userID := MustGetUserID(c)
	page, pageSize := response.GetPagination(c)
	projects, total, err := h.projectService.ListByOwner(userID, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, projects, total, page, pageSize)
}

func (h *ProjectHandler) Get(c *gin.Context) {
	userID := MustGetUserID(c)
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid project id")
		return
	}
	project, err := h.projectService.GetByID(id, userID)
	if err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, project)
}

func (h *ProjectHandler) Update(c *gin.Context) {
	userID := MustGetUserID(c)
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid project id")
		return
	}
	var input service.UpdateProjectInput
	if err := c.ShouldBindJSON(&input); err != nil {
		response.BadRequest(c, "invalid request: "+err.Error())
		return
	}
	project, err := h.projectService.Update(id, userID, &input)
	if err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, project)
}

func (h *ProjectHandler) Delete(c *gin.Context) {
	userID := MustGetUserID(c)
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid project id")
		return
	}
	if err := h.projectService.Delete(id, userID); err != nil {
		resourceError(c, err, "project not found")
		return
	}
	response.Success(c, nil)
}
