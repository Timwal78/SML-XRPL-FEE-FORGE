.PHONY: build run test lint tidy setup docker clean

BINARY=x402-gateway
GO=go

# First run: download + tidy deps (generates correct go.sum)
setup:
	$(GO) mod download
	$(GO) mod tidy

build: setup
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

dev:
	@echo "Starting gateway + dashboard in dev mode..."
	@$(MAKE) -j2 run dashboard-dev

dashboard-dev:
	cd ../dashboard && npm run dev
