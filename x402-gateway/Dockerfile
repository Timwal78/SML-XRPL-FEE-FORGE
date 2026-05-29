# ---- build stage ----
FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git ca-certificates tzdata
WORKDIR /app

# Copy go.mod first; download deps without requiring a pre-existing go.sum.
# -mod=mod lets go generate/update go.sum automatically during build.
COPY go.mod go.sum* ./
RUN GOFLAGS=-mod=mod go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -mod=mod -ldflags="-s -w" -trimpath -o /x402-gateway ./cmd/server

# ---- runtime stage ----
# Use alpine (not scratch) so Render health-check curl/wget works if needed.
FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata wget
COPY --from=builder /x402-gateway /x402-gateway
ENV TZ=UTC
EXPOSE 8080
# Run as non-root
RUN adduser -D -u 10001 appuser
USER appuser
ENTRYPOINT ["/x402-gateway"]
