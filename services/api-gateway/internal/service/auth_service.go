package service

import (
	"errors"
	"fmt"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/pkg/hash"
	"mago-agent/api-gateway/internal/pkg/jwt"
	"mago-agent/api-gateway/internal/repository"

	"github.com/google/uuid"
	"go.uber.org/zap"
	"gorm.io/gorm"
)

var ErrEmailAlreadyRegistered = errors.New("email already registered")

type AuthService struct {
	userRepo   *repository.UserRepository
	jwtManager *jwt.Manager
}

func NewAuthService(userRepo *repository.UserRepository, jwtManager *jwt.Manager) *AuthService {
	return &AuthService{userRepo: userRepo, jwtManager: jwtManager}
}

type RegisterInput struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required,min=6"`
	Name     string `json:"name" binding:"required,min=1"`
}

type LoginInput struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

type AuthResponse struct {
	AccessToken  string     `json:"access_token"`
	RefreshToken string     `json:"refresh_token"`
	ExpiresIn    int        `json:"expires_in"`
	User         model.User `json:"user"`
}

func (s *AuthService) Register(input *RegisterInput) (*AuthResponse, error) {
	// Check if email exists
	exists, err := s.userRepo.EmailExists(input.Email)
	if err != nil {
		return nil, err
	}
	if exists {
		return nil, ErrEmailAlreadyRegistered
	}

	// Hash password
	hashedPwd, err := hash.HashPassword(input.Password)
	if err != nil {
		return nil, err
	}

	// Create org first
	userID := uuid.New()
	orgID := uuid.New()

	// Create the user, workspace, and membership atomically. Returning success
	// after only part of this operation completed leaves an unusable account.
	user := &model.User{
		BaseModel: model.BaseModel{ID: userID},
		Email:     input.Email,
		Password:  hashedPwd,
		Name:      input.Name,
		Role:      "owner",
		OrgID:     &orgID,
	}
	org := &model.Organization{
		BaseModel: model.BaseModel{ID: orgID},
		Name:      input.Name + "'s Workspace",
		OwnerID:   userID,
	}
	membership := &model.Membership{UserID: userID, OrgID: orgID, Role: "owner"}

	if err := model.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(user).Error; err != nil {
			return err
		}
		if err := tx.Create(org).Error; err != nil {
			return err
		}
		return tx.Create(membership).Error
	}); err != nil {
		zap.L().Error("failed to create user workspace", zap.Error(err))
		return nil, fmt.Errorf("failed to create account: %w", err)
	}

	// Generate tokens
	tokens, err := s.jwtManager.GenerateTokenPair(user.ID, user.Email, user.Role)
	if err != nil {
		return nil, err
	}

	return &AuthResponse{
		AccessToken:  tokens.AccessToken,
		RefreshToken: tokens.RefreshToken,
		ExpiresIn:    tokens.ExpiresIn,
		User:         *user,
	}, nil
}

func (s *AuthService) Login(input *LoginInput) (*AuthResponse, error) {
	user, err := s.userRepo.FindByEmail(input.Email)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, errors.New("invalid email or password")
		}
		return nil, err
	}

	if !hash.CheckPassword(input.Password, user.Password) {
		return nil, errors.New("invalid email or password")
	}

	tokens, err := s.jwtManager.GenerateTokenPair(user.ID, user.Email, user.Role)
	if err != nil {
		return nil, err
	}

	return &AuthResponse{
		AccessToken:  tokens.AccessToken,
		RefreshToken: tokens.RefreshToken,
		ExpiresIn:    tokens.ExpiresIn,
		User:         *user,
	}, nil
}

func (s *AuthService) GetUser(userID uuid.UUID) (*model.User, error) {
	return s.userRepo.FindByID(userID)
}

func (s *AuthService) RefreshToken(refreshToken string) (*jwt.TokenPair, error) {
	claims, err := s.jwtManager.ParseRefreshToken(refreshToken)
	if err != nil {
		return nil, errors.New("invalid refresh token")
	}
	user, err := s.userRepo.FindByID(claims.UserID)
	if err != nil {
		return nil, err
	}
	return s.jwtManager.GenerateTokenPair(user.ID, user.Email, user.Role)
}
