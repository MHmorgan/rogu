
# Name of application
EXE := app

# All platforms must support amd64 and arm64, or else the
# build target needs to be updated as well.
PLATFORMS := windows linux darwin

# -s : Dead code elimination
# -w : Disable DWARF generation
# netgo : Pure Go implementation of network-related packages
# static : Create a fully statically-linked executable
FLAGS = -tags netgo,static -ldflags "-s -w" -trimpath

all: clean $(PLATFORMS)

$(PLATFORMS):
	GOOS=$@ GOARCH=arm64 go build -o $(EXE)_$@_arm64 $(FLAGS)
	GOOS=$@ GOARCH=amd64 go build -o $(EXE)_$@_amd64 $(FLAGS)

clean:
	go clean
	rm $(EXE)*
