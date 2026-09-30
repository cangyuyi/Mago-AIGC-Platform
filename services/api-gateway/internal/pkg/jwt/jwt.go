package jwt

import (
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type Claims struct {
	UserID    uuid.UUID `json:"user_id"`
	Email     string    `json:"email"`
	Role      string    `json:"role"`
	TokenType string    `json:"token_type"`
	jwt.RegisteredClaims
}

type TokenPair struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	ExpiresIn    int    `json:"expires_in"` // seconds
	TokenType    string `json:"token_type"`
}

type Manager struct {
	secret     []byte
	accessTTL  time.Duration
	refreshTTL time.Duration
}

func NewManager(secret string, accessTTLMinutes int, refreshTTLDays int) *Manager {
	return &Manager{
		secret:     []byte(secret),
		accessTTL:  time.Duration(accessTTLMinutes) * time.Minute,
		refreshTTL: time.Duration(refreshTTLDays) * 24 * time.Hour,
	}
}

func (m *Manager) GenerateTokenPair(userID uuid.UUID, email, role string) (*TokenPair, error) {
	now := time.Now()
	accessClaims := Claims{
		UserID: userID, Email: email, Role: role, TokenType: "access",
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(now.Add(m.accessTTL)),
			IssuedAt:  jwt.NewNumericDate(now),
			Issuer:    "mago-agent",
			Subject:   userID.String(),
			ID:        uuid.New().String(),
		},
	}
	accessToken, err := jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims).SignedString(m.secret)
	if err != nil {
		return nil, err
	}

	refreshClaims := Claims{
		UserID: userID, Email: email, Role: role, TokenType: "refresh",
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(now.Add(m.refreshTTL)),
			IssuedAt:  jwt.NewNumericDate(now),
			Issuer:    "mago-agent",
			Subject:   userID.String(),
			ID:        uuid.New().String(),
		},
	}
	refreshToken, err := jwt.NewWithClaims(jwt.SigningMethodHS256, refreshClaims).SignedString(m.secret)
	if err != nil {
		return nil, err
	}

	return &TokenPair{
		AccessToken: accessToken, RefreshToken: refreshToken,
		ExpiresIn: int(m.accessTTL.Seconds()), TokenType: "Bearer",
	}, nil
}

// ParseToken validates the signature and standard claims. Callers that need to
// enforce token purpose should use ParseAccessToken or ParseRefreshToken.
func (m *Manager) ParseToken(tokenString string) (*Claims, error) {
	return m.parseToken(tokenString, "")
}

func (m *Manager) ParseAccessToken(tokenString string) (*Claims, error) {
	return m.parseToken(tokenString, "access")
}

func (m *Manager) ParseRefreshToken(tokenString string) (*Claims, error) {
	return m.parseToken(tokenString, "refresh")
}

func (m *Manager) parseToken(tokenString, expectedType string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(t *jwt.Token) (interface{}, error) {
		if t.Method != jwt.SigningMethodHS256 {
			return nil, errors.New("unexpected signing method")
		}
		return m.secret, nil
	})
	if err != nil {
		return nil, err
	}
	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token")
	}
	if claims.Issuer != "mago-agent" {
		return nil, errors.New("invalid issuer")
	}
	if expectedType != "" && claims.TokenType != expectedType {
		return nil, errors.New("invalid token type")
	}
	if claims.UserID == uuid.Nil {
		return nil, errors.New("token subject is missing")
	}
	return claims, nil
}
