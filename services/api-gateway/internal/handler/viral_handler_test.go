package handler

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

type viralProxyRoundTripFunc func(*http.Request) (*http.Response, error)

func (f viralProxyRoundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) {
	return f(r)
}

func TestViralHandlerAnalyzeOmitsOptionalZeroValues(t *testing.T) {
	gin.SetMode(gin.TestMode)
	proxy := NewAgentProxy("http://agent.internal")
	proxy.client.Transport = viralProxyRoundTripFunc(func(r *http.Request) (*http.Response, error) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("read upstream request body: %v", err)
		}
		if got, want := string(body), `{"url":"https://example.com/video"}`; got != want {
			t.Fatalf("upstream request body = %s, want %s", got, want)
		}
		return &http.Response{
			StatusCode: http.StatusAccepted,
			Header:     http.Header{"Content-Type": []string{"application/json"}},
			Body:       io.NopCloser(bytes.NewReader([]byte(`{"task_id":"analyze_test"}`))),
			Request:    r,
		}, nil
	})

	r := gin.New()
	r.POST("/viral-videos/analyze", func(c *gin.Context) {
		NewViralHandler(nil, proxy).Analyze(c)
	})

	req := httptest.NewRequest(http.MethodPost, "/viral-videos/analyze", bytes.NewBufferString(`{"url":"https://example.com/video"}`))
	req.Header.Set("Content-Type", "application/json")
	resp := httptest.NewRecorder()
	r.ServeHTTP(resp, req)

	if resp.Code != http.StatusAccepted {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	if got, want := resp.Body.String(), `{"task_id":"analyze_test"}`; got != want {
		t.Fatalf("response body = %s, want %s", got, want)
	}
}
