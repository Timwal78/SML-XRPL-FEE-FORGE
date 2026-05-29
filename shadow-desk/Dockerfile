# Stage 1: Build a statically-linked binary with no CGO dependencies.
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Copy module definition first to cache the (empty) dependency layer.
COPY go.mod ./
# go.sum is omitted intentionally: this module has no external dependencies.

COPY . .

# -ldflags="-w -s" strips debug info and symbol table to minimise binary size.
# CGO_ENABLED=0 produces a fully static binary suitable for the scratch image.
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-w -s" -o shadow-desk ./cmd/server

# Stage 2: Minimal runtime — scratch + SSL bundle.
# Using scratch gives us the smallest possible attack surface:
# no shell, no package manager, no unused libraries.
FROM scratch

# Copy the CA certificate bundle so HTTPS calls to the x402 facilitator work.
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

COPY --from=builder /build/shadow-desk /shadow-desk

# Run as UID 65534 (nobody) — numeric UID works in scratch without /etc/passwd.
USER 65534:65534

EXPOSE 8080

ENTRYPOINT ["/shadow-desk"]
