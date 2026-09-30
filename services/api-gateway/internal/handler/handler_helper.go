package handler

import (
	"mago-agent/api-gateway/internal/middleware"
	"mago-agent/api-gateway/internal/pkg/response"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func MustGetUserID(c *gin.Context) uuid.UUID {
	userID, exists := c.Get(middleware.CtxUserID)
	if !exists {
		response.Unauthorized(c, "user not authenticated")
		return uuid.Nil
	}
	parsed, ok := userID.(uuid.UUID)
	if !ok || parsed == uuid.Nil {
		response.Unauthorized(c, "invalid user identity")
		return uuid.Nil
	}
	return parsed
}

// UserID returns the authenticated user id and reports whether it is present.
// Unlike MustGetUserID it does not write a response, so handlers can return
// early instead of continuing with a nil user id.
func UserID(c *gin.Context) (uuid.UUID, bool) {
	raw, exists := c.Get(middleware.CtxUserID)
	if !exists {
		return uuid.Nil, false
	}
	parsed, ok := raw.(uuid.UUID)
	if !ok || parsed == uuid.Nil {
		return uuid.Nil, false
	}
	return parsed, true
}
