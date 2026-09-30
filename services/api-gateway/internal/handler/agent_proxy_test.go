package handler

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) {
	return f(r)
}

func TestAgentProxyForwardsJSONAndAuthorization(t *testing.T) {
	gin.SetMode(gin.TestMode)
	proxy := NewAgentProxy("http://agent.internal")
	proxy.client.Transport = roundTripFunc(func(r *http.Request) (*http.Response, error) {
		if r.Method != http.MethodPost || r.URL.Path != "/api/v1/topic-recommendations/generate" {
			t.Fatalf("unexpected upstream request: %s %s", r.Method, r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer test-token" {
			t.Fatalf("authorization header = %q", got)
		}
		body, _ := io.ReadAll(r.Body)
		if string(body) != `{"count":1}` {
			t.Fatalf("request body = %s", body)
		}
		return &http.Response{
			StatusCode: http.StatusAccepted,
			Header:     http.Header{"Content-Type": []string{"application/json"}},
			Body:       io.NopCloser(bytes.NewReader([]byte(`{"ok":true}`))),
			Request:    r,
		}, nil
	})

	r := gin.New()
	r.POST("/proxy", func(c *gin.Context) {
		c.Request.Header.Set("Authorization", "Bearer test-token")
		proxy.ForwardJSON(c, http.MethodPost, "/topic-recommendations/generate", gin.H{"count": 1})
	})

	req := httptest.NewRequest(http.MethodPost, "/proxy", nil)
	resp := httptest.NewRecorder()
	r.ServeHTTP(resp, req)
	if resp.Code != http.StatusAccepted {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	if got := resp.Body.String(); got != `{"ok":true}` {
		t.Fatalf("response body = %s", got)
	}
}

// sseRecorder records whether the handler flushed mid-stream, which is what
// keeps token-level SSE real-time instead of collapsing into one delivery.
type sseRecorder struct {
	*httptest.ResponseRecorder
	flushes int
}

func (r *sseRecorder) Flush() {
	r.flushes++
	r.ResponseRecorder.Flush()
}

func TestAgentProxyFlushesSSEStream(t *testing.T) {
	gin.SetMode(gin.TestMode)
	proxy := NewAgentProxy("http://agent.internal")

	body := "data: chunk-1\n\ndata: chunk-2\n\ndata: [DONE]\n\n"
	proxy.client.Transport = roundTripFunc(func(r *http.Request) (*http.Response, error) {
		return &http.Response{
			StatusCode: http.StatusOK,
			Header:     http.Header{"Content-Type": []string{"text/event-stream"}},
			Body:       io.NopCloser(strings.NewReader(body)),
			Request:    r,
		}, nil
	})

	rec := &sseRecorder{ResponseRecorder: httptest.NewRecorder()}
	c, _ := gin.CreateTestContext(rec)
	c.Request = httptest.NewRequest(http.MethodPost, "/proxy", nil)
	proxy.ForwardJSON(c, http.MethodPost, "/run", gin.H{"mode": "quick"})

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
	if got := rec.Body.String(); got != body {
		t.Fatalf("stream body not forwarded intact: %q", got)
	}
	if rec.flushes == 0 {
		t.Fatal("SSE response was never flushed; client would not see token-level streaming")
	}
}
