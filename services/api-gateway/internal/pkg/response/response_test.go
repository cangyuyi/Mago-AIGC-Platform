package response

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func init() { gin.SetMode(gin.TestMode) }

// A committed response must never be overwritten by a later helper call, which
// happens when a handler keeps running after an earlier 401 was written.
func TestErrorDoesNotOverwriteCommittedResponse(t *testing.T) {
	rec := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(rec)

	Unauthorized(c, "user not authenticated")
	NotFound(c, "script not found")
	Success(c, gin.H{"leak": true})

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusUnauthorized)
	}
	body := rec.Body.String()
	if want := `"code":40100`; !contains(body, want) {
		t.Fatalf("body %q does not contain %s", body, want)
	}
	if contains(body, "40400") || contains(body, "leak") {
		t.Fatalf("second response leaked into body: %s", body)
	}
}

func TestSuccessWritesOnce(t *testing.T) {
	rec := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(rec)

	Success(c, gin.H{"ok": 1})

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
}

func contains(haystack, needle string) bool {
	return len(haystack) >= len(needle) && (haystack == needle || indexOf(haystack, needle) >= 0)
}

func indexOf(haystack, needle string) int {
	for i := 0; i+len(needle) <= len(haystack); i++ {
		if haystack[i:i+len(needle)] == needle {
			return i
		}
	}
	return -1
}
