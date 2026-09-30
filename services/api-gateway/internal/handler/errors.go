package handler

import (
	"errors"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/repository"
)

// resourceError maps missing and unauthorized resources to the same response so
// callers cannot enumerate another user's IDs. Unexpected errors remain 500.
func resourceError(c *gin.Context, err error, notFoundMessage string) {
	if errors.Is(err, gorm.ErrRecordNotFound) || errors.Is(err, repository.ErrAccessDenied) {
		response.NotFound(c, notFoundMessage)
		return
	}
	response.InternalError(c, err.Error())
}
