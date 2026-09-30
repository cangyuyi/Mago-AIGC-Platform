package handler

import (
	"errors"

	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/service"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type AuthHandler struct {
	authService *service.AuthService
}

func NewAuthHandler(authService *service.AuthService) *AuthHandler {
	return &AuthHandler{authService: authService}
}

func (h *AuthHandler) Register(c *gin.Context) {
	var input service.RegisterInput
	if err := c.ShouldBindJSON(&input); err != nil {
		response.BadRequest(c, "invalid request: "+err.Error())
		return
	}
	resp, err := h.authService.Register(&input)
	if err != nil {
		if errors.Is(err, service.ErrEmailAlreadyRegistered) {
			response.Conflict(c, err.Error())
			return
		}
		zap.L().Error("registration failed", zap.Error(err))
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, resp)
}

func (h *AuthHandler) Login(c *gin.Context) {
	var input service.LoginInput
	if err := c.ShouldBindJSON(&input); err != nil {
		response.BadRequest(c, "invalid request: "+err.Error())
		return
	}
	resp, err := h.authService.Login(&input)
	if err != nil {
		// Do not expose database or token-provider errors through the auth API.
		// Keep the response generic to avoid both information leaks and account
		// enumeration, while retaining the original error in server logs.
		zap.L().Warn("login failed", zap.Error(err))
		response.Unauthorized(c, "invalid email or password")
		return
	}
	response.Success(c, resp)
}

func (h *AuthHandler) Me(c *gin.Context) {
	userID := MustGetUserID(c)
	user, err := h.authService.GetUser(userID)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, user)
}

func (h *AuthHandler) Refresh(c *gin.Context) {
	var body struct {
		RefreshToken string `json:"refresh_token" binding:"required"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		response.BadRequest(c, "refresh_token required")
		return
	}
	tokens, err := h.authService.RefreshToken(body.RefreshToken)
	if err != nil {
		// Refresh failures may originate from JWT parsing, the database, or
		// token generation; expose only a stable client-facing error.
		zap.L().Warn("refresh token rejected", zap.Error(err))
		response.Unauthorized(c, "invalid refresh token")
		return
	}
	response.Success(c, tokens)
}
