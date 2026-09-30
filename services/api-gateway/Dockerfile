# ---- Build stage ----
FROM golang:1.22-alpine AS builder
WORKDIR /app
RUN apk add --no-cache git gcc musl-dev

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Build
COPY . .
ARG TARGETARCH
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags="-s -w" -o /api-gateway ./cmd/server

# ---- Runtime stage ----
FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata && adduser -D -H appuser
WORKDIR /app
COPY --from=builder /api-gateway /app/api-gateway
COPY migrations/ /app/migrations/
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -qO- http://localhost:8080/health || exit 1
ENTRYPOINT ["/app/api-gateway"]
