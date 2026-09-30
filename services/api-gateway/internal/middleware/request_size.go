package middleware

import (
	"bytes"
	"io"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

// RequestSizeLimit limits the request body size (default 10MB).
func RequestSizeLimit(maxSizeBytes int64) gin.HandlerFunc {
	if maxSizeBytes <= 0 {
		maxSizeBytes = 10 * 1024 * 1024 // 10MB default
	}
	return func(c *gin.Context) {
		// Check Content-Length header first if available
		if cl := c.GetHeader("Content-Length"); cl != "" {
			size, err := strconv.ParseInt(cl, 10, 64)
			if err == nil && size > maxSizeBytes {
				c.AbortWithStatusJSON(http.StatusRequestEntityTooLarge, gin.H{
					"error":       "request_too_large",
					"max_size_mb": maxSizeBytes / 1024 / 1024,
					"code":        413,
				})
				return
			}
		}

		// Wrap body to enforce limit while reading
		c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, maxSizeBytes)

		// Read body into buffer so it can be re-read by handlers
		body, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusRequestEntityTooLarge, gin.H{
				"error":       "request_too_large",
				"max_size_mb": maxSizeBytes / 1024 / 1024,
				"code":        413,
			})
			return
		}
		c.Request.Body = io.NopCloser(bytes.NewBuffer(body))
		c.Next()
	}
}
