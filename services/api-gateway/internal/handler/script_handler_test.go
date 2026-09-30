package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/middleware"
)

func init() { gin.SetMode(gin.TestMode) }

// A request without a resolved user must be answered with exactly one 401 body
// and must never reach the persistence layer.
func TestReplaceShotsRejectsUnauthenticatedRequest(t *testing.T) {
	h := &ScriptHandler{}

	rec := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(rec)
	c.Request = httptest.NewRequest(http.MethodPut, "/api/v1/storyboards/"+uuid.New().String()+"/shots", nil)
	c.Params = gin.Params{{Key: "id", Value: uuid.New().String()}}

	h.ReplaceShots(c)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rec.Code)
	}
	var payload map[string]interface{}
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("invalid json body %q: %v", rec.Body.String(), err)
	}
	if code := payload["code"]; code != float64(40100) {
		t.Fatalf("body = %v, want error code 40100", payload)
	}
}

func TestReplaceShotsRejectsMalformedStoryboardID(t *testing.T) {
	h := &ScriptHandler{}

	rec := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(rec)
	c.Request = httptest.NewRequest(http.MethodPut, "/api/v1/storyboards/not-a-uuid/shots", nil)
	c.Params = gin.Params{{Key: "id", Value: "not-a-uuid"}}
	c.Set(middleware.CtxUserID, uuid.New())

	h.ReplaceShots(c)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}
