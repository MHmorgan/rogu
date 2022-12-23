package items

import (
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/sh"
	"github.com/mhmorgan/rogu/utils"
	"os"
	"strings"
)

func fileItems() (items []Item, err error) {
	cfg := config.Get()

	for name, val := range cfg.Files {
		item := fileItem{
			name:     name,
			priority: val.Priority,
			url:      val.Source,
			dst:      val.Destination,
			mode:     val.Mode,
		}
		if item.mode == 0 {
			item.mode = 0644
		}
		items = append(items, item)
	}
	return
}

func fileChecker(name, url, dst string) func() error {
	home := utils.Home()
	dst = strings.Replace(dst, "~", home, 1)

	return func() error {
		if resp, _, err := utils.UrlExists(url); err != nil {
			return err
		} else if resp != 200 {
			return fmt.Errorf("%s: bad URL (response %d): %q", name, resp, url)
		}

		if ok := utils.PathExists(dst); !ok {
			return fmt.Errorf("%s: %w", dst, os.ErrNotExist)
		}
		return nil
	}
}

func fileInstaller(srcUrl, dst string, mode int) func() error {
	// Handle compression, based on file extension
	var curl string
	if strings.HasSuffix(srcUrl, ".gz") {
		curl = fmt.Sprintf("curl -sSL %s | gzcat > %s ;", srcUrl, dst)
	} else if strings.HasSuffix(srcUrl, ".bz2") {
		curl = fmt.Sprintf("curl -sSL %s | bzcat > %s ;", srcUrl, dst)
	} else {
		curl = fmt.Sprintf("curl -sSL %s -o %s ;", srcUrl, dst)
	}

	chmod := fmt.Sprintf("chmod 0%o %s ;", mode, dst)
	return func() error {
		resp, ok, err := utils.UrlExists(srcUrl)
		if err != nil {
			return err
		}
		if !ok {
			return fmt.Errorf("URL %q does not exist (response %d)", srcUrl, resp)
		}
		return sh.Runf("%s%s", curl, chmod)
	}
}

// File item

type fileItem struct {
	name     string
	priority int
	url      string
	dst      string
	mode     int
}

func (f fileItem) String() string {
	return f.name
}

func (f fileItem) Name() string {
	return f.name
}

func (f fileItem) Priority() int {
	return f.priority
}

func (f fileItem) Type() ItemType {
	return FileItem
}

func (f fileItem) Handlers() ItemHandlers {
	h := ItemHandlers{
		Check:   fileChecker(f.name, f.url, f.dst),
		Install: fileInstaller(f.url, f.dst, f.mode),
		Update:  fileInstaller(f.url, f.dst, f.mode),
	}

	h.IsInstalled = func() (bool, error) {
		home := utils.Home()
		f.dst = strings.Replace(f.dst, "~", home, 1)
		return utils.PathExists(f.dst), nil
	}

	h.Uninstall = func() error {
		return sh.Runf("rm -f %s", f.dst)
	}

	return h
}
