package utils

import (
	"github.com/mhmorgan/rogu/sh"
	log "github.com/mhmorgan/termlog"
	"os"
	"path/filepath"
)

// fs provides simplified functionality for the filesystem
// which should reduce boilerplate code. Mainly for error
// handling.

// Home returns the home directory of the current user,
// or calls log.Fatal if it cannot be determined.
func Home() string {
	home, err := os.UserHomeDir()
	if err != nil {
		log.Fatal(err)
	}
	return home
}

// RelHome returns an absolute path of the given path
// relative to the home directory.
func RelHome(path string) string {
	home, err := os.UserHomeDir()
	if err != nil {
		log.Fatal(err)
	}
	return filepath.Join(home, path)
}

// CdHome changes the current working directory to the
// home directory of the current user, or calls log.Fatal
// if it cannot be determined.
func CdHome() {
	home, err := os.UserHomeDir()
	if err != nil {
		log.Fatal(err)
	}
	if err := os.Chdir(home); err != nil {
		log.Fatal(err)
	}
}

// Cd changes to the given directory, or calls log.Fatal.
func Cd(path string) {
	if err := os.Chdir(path); err != nil {
		log.Fatal(err)
	}
}

// PathExists returns true if the given path exists.
func PathExists(path string) bool {
	_, err := os.Stat(path)
	if err == nil {
		return true
	}
	if !os.IsNotExist(err) {
		panic(err)
	}
	return false
}

// Backup backs up the given file by copying it to a new file
// with the same name and a tilde appended.
func Backup(path string) error {
	dst := path + "~"
	_, _, err := sh.Execf("cp %s %s", path, dst)
	return err
}
