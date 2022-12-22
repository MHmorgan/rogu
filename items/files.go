package items

import (
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
			Update:      fileUpdater(val.Source, val.Destination),
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
	return func() error {
		return sh.Runf("set -x\ncurl -sSL %s -o %s\nchmod 0%o %s", srcUrl, dst, mode, dst)
	}
}

func fileUninstaller(path string) func() error {
	return func() error {
		return sh.Runf("rm -f %s", path)
	}
}

func fileUpdater(src, dst string) func() error {
	return func() error {
		return sh.Runf("set -x\ncurl -sSL %s -o %s", src, dst)
	}
}
