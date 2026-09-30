package handler

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestTrendHandlerCrawlNowForwardsJSONFilters(t *testing.T) {
	gin.SetMode(gin.TestMode)
	proxy := NewAgentProxy("http://agent.internal")
	proxy.client.Transport = roundTripFunc(func(r *http.Request) (*http.Response, error) {
		if r.Method != http.MethodPost || r.URL.Path != "/api/v1/trends/crawl-now" {
			t.Fatalf("unexpected upstream request: %s %s", r.Method, r.URL.Path)
		}
		var payload map[string]string
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("decode upstream body: %v", err)
		}
		if payload["platform"] != "douyin" || payload["category"] != "beauty" {
			t.Fatalf("upstream payload = %#v", payload)
		}
		return &http.Response{
			StatusCode: http.StatusAccepted,
			Header:     http.Header{"Content-Type": []string{"application/json"}},
			Body:       io.NopCloser(bytes.NewBufferString(`{"task_id":"crawl_test"}`)),
			Request:    r,
		}, nil
	})

	r := gin.New()
	r.POST("/trends/crawl-now", func(c *gin.Context) {
		NewTrendHandler(nil, nil, proxy).CrawlNow(c)
	})
	req := httptest.NewRequest(http.MethodPost, "/trends/crawl-now", bytes.NewBufferString(`{"platform":"douyin","category":"beauty"}`))
	req.Header.Set("Content-Type", "application/json")
	resp := httptest.NewRecorder()
	r.ServeHTTP(resp, req)

	if resp.Code != http.StatusAccepted {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
}
