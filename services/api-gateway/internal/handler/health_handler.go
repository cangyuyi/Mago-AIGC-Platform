package handler

import (
	"mago-agent/api-gateway/internal/config"
	"mago-agent/api-gateway/internal/pkg/response"

	"github.com/gin-gonic/gin"
)

type HealthHandler struct {
	cfg *config.Config
}

func NewHealthHandler(cfg *config.Config) *HealthHandler {
	return &HealthHandler{cfg: cfg}
}

func (h *HealthHandler) Health(c *gin.Context) {
	response.Success(c, gin.H{
		"service": h.cfg.App.Name,
		"version": h.cfg.App.Version,
		"env":     h.cfg.Server.Env,
		"status":  "ok",
	})
}
