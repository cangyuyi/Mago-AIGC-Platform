package handler

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
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
