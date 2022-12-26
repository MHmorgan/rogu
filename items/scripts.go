package items

import (
	"errors"
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/sh"
)

func init() {
	itemsFactories = append(itemsFactories, scriptItems)
}

func scriptItems() (items []Item, err error) {
	cfg := config.Get()

	for name, val := range cfg.Scripts {
		item := Script{
			name:              name,
			priority:          val.Priority,
			checkCode:         val.Check,
			isInstalledCode:   val.IsInstalled,
			installCode:       val.Install,
			uninstallCode:     val.Uninstall,
			updateCode:        val.Update,
			updateWithInstall: val.UpdateWithInstall,
		}
		items = append(items, item)
	}
	return
}

// Script item

type Script struct {
	name              string
	priority          int
	checkCode         string // Defaults to IsInstalled
	isInstalledCode   string
	installCode       string
	uninstallCode     string // Optional
	updateCode        string // Optional
	updateWithInstall bool
}

func (i Script) Name() string {
	return i.name
}

func (i Script) Priority() int {
	return i.priority
}

func (i Script) Type() ItemType {
	return ScriptItem
}

func (i Script) Handlers() ItemHandlers {
	h := ItemHandlers{
		IsInstalled: i.isInstalled(),
		Check:       i.checker(),
		Install:     i.installer(),
		Uninstall:   i.uninstaller(),
		Update:      i.updater(),
	}
	if i.updateWithInstall {
		h.Update = h.Install
	}
	return h
}

// checker returns a function which will checker the script item.
//
// The checks are:
//  1. Check if the script has isInstalledCode
//  2. Run the checkCode or, if empty, the isInstalledCode
func (i Script) checker() Fn {
	var code string
	if i.checkCode != "" {
		code = i.checkCode
	} else {
		code = i.isInstalledCode
	}

	return func() error {
		if i.installCode == "" {
			return NoInstalledCheckError{i.name}
		}
		b, exitCode, err := sh.Exec(code)
		if err != nil {
			return err
		}
		if exitCode != 0 {
			s := fmt.Sprintf("Check failed with exit code %d", exitCode)
			if b.Len() > 0 {
				s += " and output:\n" + b.String()
			}
			return errors.New(s)
		}
		return nil
	}
}

// isInstalled returns a function which will execute
// the isInstalledCode.
func (i Script) isInstalled() BoolFn {
	if i.isInstalledCode != "" {
		return nil
	}
	return func() (bool, error) {
		_, code, err := sh.Exec(i.isInstalledCode)
		return code == 0, err
	}
}

func (i Script) installer() func() error {
	if i.installCode == "" {
		return nil
	}
	return func() error {
		return sh.Run(i.installCode)
	}
}

func (i Script) uninstaller() func() error {
	if i.uninstallCode == "" {
		return nil
	}
	return func() error {
		return sh.Run(i.uninstallCode)
	}
}

func (i Script) updater() func() error {
	if i.updateCode == "" {
		return nil
	}
	return func() error {
		return sh.Run(i.updateCode)
	}
}

func (i Script) String() string {
	return i.name
}
