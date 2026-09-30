package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

func TestLoggerDoesNotPanicWithoutRequestID(t *testing.T) {
	previous := zap.L()
	zap.ReplaceGlobals(zap.NewNop())
	defer zap.ReplaceGlobals(previous)

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(Logger())
	router.GET("/health", func(c *gin.Context) {
		c.Status(http.StatusNoContent)
	})

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	resp := httptest.NewRecorder()

	didPanic := false
	func() {
		defer func() {
			if recover() != nil {
				didPanic = true
			}
		}()
		router.ServeHTTP(resp, req)
	}()

	if didPanic {
		t.Fatal("logger panicked when request_id was not set")
	}
	if resp.Code != http.StatusNoContent {
		t.Fatalf("expected status %d, got %d", http.StatusNoContent, resp.Code)
	}
}
