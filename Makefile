vet:
	@go vet ./...

build:
	@go build -o bin/ff12rng ./cmd/ff12rng

run: build
	@bin/ff12rng

tidy:
	@go mod tidy

.PHONY = vet build run tidy
