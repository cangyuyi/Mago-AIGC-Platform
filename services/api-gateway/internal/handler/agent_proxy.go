package handler

import (
	"bufio"
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"mago-agent/api-gateway/internal/pkg/response"
)

// AgentProxy forwards authenticated gateway requests to the Python agent.
// Keeping this in the gateway makes the public API consistent: clients can use
// either the direct /api/agent routes or the equivalent /api/v1 routes without
// receiving a fabricated task id that can never complete.
type AgentProxy struct {
	baseURL string
	client  *http.Client
}

func NewAgentProxy(baseURL string) *AgentProxy {
	return &AgentProxy{
		baseURL: strings.TrimRight(strings.TrimSpace(baseURL), "/"),
		client: &http.Client{
			Timeout: 10 * time.Minute,
		},
	}
}

func (p *AgentProxy) ForwardJSON(c *gin.Context, method, path string, payload any) {
	var body io.Reader
	if payload != nil {
		encoded, err := json.Marshal(payload)
		if err != nil {
			response.BadRequest(c, "invalid agent request")
			return
		}
		body = bytes.NewReader(encoded)
	}
	p.forward(c, method, path, body, payload != nil)
}

func (p *AgentProxy) Forward(c *gin.Context, method, path string) {
	p.forward(c, method, path, nil, false)
}

func (p *AgentProxy) forward(c *gin.Context, method, path string, body io.Reader, hasJSONBody bool) {
	if p == nil || p.baseURL == "" {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "agent service is not configured"})
		return
	}

	req, err := http.NewRequestWithContext(c.Request.Context(), method, p.baseURL+"/api/v1"+path, body)
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "agent service request could not be created"})
		return
	}
	if authorization := c.GetHeader("Authorization"); authorization != "" {
		req.Header.Set("Authorization", authorization)
	}
	if requestID := c.GetHeader("X-Request-ID"); requestID != "" {
		req.Header.Set("X-Request-ID", requestID)
	}
	if hasJSONBody {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := p.client.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "agent service unavailable"})
		return
	}
	defer resp.Body.Close()

	for key, values := range resp.Header {
		if key == "Content-Length" || key == "Connection" {
			continue
		}
		for _, value := range values {
			c.Header(key, value)
		}
	}
	c.Status(resp.StatusCode)
	streamResponse(c, resp)
}

// streamResponse forwards the upstream body to the client.
//
// For `text/event-stream` responses it must flush after every chunk, otherwise
// Go's default copy buffering collapses the Agent's token-level SSE stream into
// a single delivery at the end and clients lose real-time streaming. For all
// other content types it falls back to a plain copy.
func streamResponse(c *gin.Context, resp *http.Response) {
	if !strings.Contains(strings.ToLower(resp.Header.Get("Content-Type")), "text/event-stream") {
		_, _ = io.Copy(c.Writer, resp.Body)
		return
	}

	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		// Server/transport cannot flush; degrade to a single copy rather than fail.
		_, _ = io.Copy(c.Writer, resp.Body)
		return
	}

	reader := bufio.NewReader(resp.Body)
	buffer := make([]byte, 4096)
	for {
		n, readErr := reader.Read(buffer)
		if n > 0 {
			if _, writeErr := c.Writer.Write(buffer[:n]); writeErr != nil {
				return
			}
			flusher.Flush()
		}
		if readErr != nil {
			return
		}
	}
}
