# ---- build stage ----
FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git ca-certificates tzdata
WORKDIR /app

COPY go.mod ./
RUN GOFLAGS=-mod=mod go mod download

COPY . .
# Remove stale go.sum — -mod=mod cannot overwrite existing wrong hashes,
# so we wipe it and let the build regenerate it from the module cache.
RUN rm -f go.sum
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -mod=mod -ldflags="-s -w" -trimpath -o /x402-gateway ./cmd/server

# ---- runtime stage ----
FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata wget
COPY --from=builder /x402-gateway /x402-gateway
ENV TZ=UTC
EXPOSE 8080
RUN adduser -D -u 10001 appuser
USER appuser
ENTRYPOINT ["/x402-gateway"]
