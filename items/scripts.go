package items

import (
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/sh"
)

func scriptItems() (items []Item, err error) {
	cfg := config.Get()

	for name, val := range cfg.Scripts {
		item := Item{
			Name:     name,
			Type:     ScriptItem,
			Priority: val.Priority,
		}
		if val.Check != "" {
			item.IsInstalled = scriptChecker(val.Check)
		}
		if val.Install != "" {
			item.Install = scriptInstaller(val.Install)
		}
		if val.Uninstall != "" {
			item.Uninstall = scriptUninstaller(val.Uninstall)
		}
		if val.Update != "" {
			item.Update = scriptUpdater(val.Update)
		}
		items = append(items, item)
	}
	return
}

func scriptChecker(code string) func() (bool, error) {
	return func() (bool, error) {
		_, code, err := sh.Exec(code)
		return code == 0, err
	}
}

func scriptInstaller(code string) func() error {
	return func() error {
		return sh.Run(code)
	}
}

func scriptUninstaller(code string) func() error {
	return func() error {
		return sh.Run(code)
	}
}

func scriptUpdater(code string) func() error {
	return func() error {
		return sh.Run(code)
	}
}
