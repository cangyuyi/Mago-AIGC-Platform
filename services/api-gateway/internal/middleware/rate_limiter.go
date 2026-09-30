package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// simpleTokenBucket 标准库实现的令牌桶限流，无需外部依赖
type simpleTokenBucket struct {
	capacity   int
	tokens     float64
	refillRate float64 // tokens per second
	lastRefill time.Time
	mu         sync.Mutex
}

func newTokenBucket(rps float64, burst int) *simpleTokenBucket {
	return &simpleTokenBucket{
		capacity:   burst,
		tokens:     float64(burst),
		refillRate: rps,
		lastRefill: time.Now(),
	}
}

func (tb *simpleTokenBucket) allow() bool {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(tb.lastRefill).Seconds()
	tb.tokens += elapsed * tb.refillRate
	if tb.tokens > float64(tb.capacity) {
		tb.tokens = float64(tb.capacity)
	}
	tb.lastRefill = now

	if tb.tokens >= 1 {
		tb.tokens -= 1
		return true
	}
	return false
}

// RateLimiter creates a per-IP token bucket rate limiter.
// rps: requests per second allowed
// burst: maximum burst size
func RateLimiter(rps float64, burst int) gin.HandlerFunc {
	limiters := make(map[string]*simpleTokenBucket)
	var mu sync.Mutex

	// Periodically cleanup old limiters
	go func() {
		for {
			time.Sleep(10 * time.Minute)
			mu.Lock()
			for ip := range limiters {
				delete(limiters, ip)
			}
			mu.Unlock()
		}
	}()

	getLimiter := func(ip string) *simpleTokenBucket {
		mu.Lock()
		defer mu.Unlock()
		limiter, exists := limiters[ip]
		if !exists {
			limiter = newTokenBucket(rps, burst)
			limiters[ip] = limiter
		}
		return limiter
	}

	return func(c *gin.Context) {
		ip := c.ClientIP()
		limiter := getLimiter(ip)
		if !limiter.allow() {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"error": "rate_limit_exceeded",
				"code":  429,
			})
			return
		}
		c.Next()
	}
}

// GlobalRateLimiter applies a global rate limit across all requests.
func GlobalRateLimiter(rps float64, burst int) gin.HandlerFunc {
	limiter := newTokenBucket(rps, burst)
	return func(c *gin.Context) {
		if !limiter.allow() {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"error": "global_rate_limit_exceeded",
				"code":  429,
			})
			return
		}
		c.Next()
	}
}
