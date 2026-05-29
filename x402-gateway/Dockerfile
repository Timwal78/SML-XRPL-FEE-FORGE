# ---- build stage ----
FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git ca-certificates tzdata
WORKDIR /app

# Copy only go.mod — let Go regenerate go.sum cleanly during download.
# -mod=mod allows Go to create/update go.sum without a pre-existing lockfile.
COPY go.mod ./
RUN GOFLAGS=-mod=mod go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -mod=mod -ldflags="-s -w" -trimpath -o /x402-gateway ./cmd/server

# ---- runtime stage ----
# Use alpine (not scratch) so Render health-check wget works.
FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata wget
COPY --from=builder /x402-gateway /x402-gateway
ENV TZ=UTC
EXPOSE 8080
# Run as non-root
RUN adduser -D -u 10001 appuser
USER appuser
ENTRYPOINT ["/x402-gateway"]
