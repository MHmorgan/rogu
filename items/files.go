package items

import (
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/fs"
	"github.com/mhmorgan/rogu/sh"
	"strings"
)

func fileItems() (items []Item, err error) {
	cfg := config.Get()

	for name, val := range cfg.Files {
		item := Item{
			Name:        name,
			Type:        FileItem,
			Priority:    val.Priority,
			IsInstalled: fileChecker(val.Destination),
			Install:     fileInstaller(val.Source, val.Destination, val.Mode),
			Uninstall:   fileUninstaller(val.Destination),
			Update:      fileInstaller(val.Source, val.Destination, val.Mode),
		}
		items = append(items, item)
	}
	return
}

func fileChecker(path string) func() (bool, error) {
	home := fs.Home()
	path = strings.Replace(path, "~", home, 1)
	return func() (bool, error) {
		return fs.Exists(path), nil
	}
}

func fileInstaller(srcUrl, dst string, mode int) func() error {

	// Handle compression, based on file extension
	var curl string
	if strings.HasSuffix(srcUrl, ".gz") {
		curl = fmt.Sprintf("curl -sSL %s | gzcat > %s", srcUrl, dst)
	} else if strings.HasSuffix(srcUrl, ".bz2") {
		curl = fmt.Sprintf("curl -sSL %s | bzcat > %s", srcUrl, dst)
	} else {
		curl = fmt.Sprintf("curl -sSL %s -o %s", srcUrl, dst)
	}

	chmod := fmt.Sprintf("chmod 0%o %s", mode, dst)
	return func() error {
		return sh.Runf("set -x\n%s\n%s", curl, chmod)
	}
}

func fileUninstaller(path string) func() error {
	return func() error {
		return sh.Runf("rm -f %s", path)
	}
}
