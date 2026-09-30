# Build stage
FROM golang:1.27-alpine AS builder

RUN apk add --no-cache gcc musl-dev

WORKDIR /build

# Copy go mod files first for caching
COPY services/api-gateway/go.mod services/api-gateway/go.sum ./
RUN go mod download

# Copy source
COPY services/api-gateway/ ./

# Build binary
ARG TARGETARCH
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags="-s -w" -o /app/server ./cmd/server/

# Runtime stage
FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata curl bash && \
    adduser -D -H -h /app appuser

WORKDIR /app

COPY --from=builder /app/server ./server
COPY services/api-gateway/migrations/ ./migrations/
COPY scripts/ ./scripts/

RUN chmod +x ./server && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

CMD ["./server"]
