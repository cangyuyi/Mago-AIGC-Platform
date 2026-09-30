package middleware

import (
	"strings"

	"mago-agent/api-gateway/internal/pkg/jwt"
	"mago-agent/api-gateway/internal/pkg/response"

	"github.com/gin-gonic/gin"
)

const (
	CtxUserID    = "user_id"
	CtxUserEmail = "user_email"
	CtxUserRole  = "user_role"
)

func AuthMiddleware(jwtManager *jwt.Manager) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Unauthorized(c, "missing authorization header")
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			response.Unauthorized(c, "invalid authorization format")
			return
		}

		claims, err := jwtManager.ParseAccessToken(parts[1])
		if err != nil {
			response.Unauthorized(c, "invalid or expired token")
			return
		}

		c.Set(CtxUserID, claims.UserID)
		c.Set(CtxUserEmail, claims.Email)
		c.Set(CtxUserRole, claims.Role)
		c.Next()
	}
}

// RequireRoles restricts an authenticated route to one of the supplied roles.
// It must be registered after AuthMiddleware so the role is available in the context.
func RequireRoles(roles ...string) gin.HandlerFunc {
	allowed := make(map[string]struct{}, len(roles))
	for _, role := range roles {
		allowed[role] = struct{}{}
	}
	return func(c *gin.Context) {
		role, exists := c.Get(CtxUserRole)
		roleName, ok := role.(string)
		if !exists || !ok || roleName == "" {
			response.Unauthorized(c, "user role is missing")
			return
		}
		if _, ok := allowed[roleName]; !ok {
			response.Forbidden(c, "insufficient permissions")
			return
		}
		c.Next()
	}
}
