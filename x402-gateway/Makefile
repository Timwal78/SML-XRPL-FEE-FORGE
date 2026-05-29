.PHONY: build run test lint tidy docker

BINARY=x402-gateway
GO=go

build:
	$(GO) build -ldflags="-s -w" -trimpath -o $(BINARY) ./cmd/server

run:
	$(GO) run ./cmd/server

test:
	$(GO) test ./... -race -count=1 -timeout 60s

lint:
	which golangci-lint || go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	golangci-lint run ./...

tidy:
	$(GO) mod tidy

clean:
	rm -f $(BINARY)

docker:
	docker build -t sml/x402-gateway:latest .

docker-push:
	docker push sml/x402-gateway:latest
