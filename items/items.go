//go:generate stringer -type=ItemType

// Package items implement the functionality for handling
// the user items defined in the config file.
//
// Install scripts are items which define shell
// scripts/commands to be run for installing, uninstalling,
// or updating items.
//
// Files are items which define files to be managed by Rogu,
// which will install and keep them up to date.
package items

import (
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/dotfiles"
	"sort"
)

// All returns a list of all items defined in the config.
//
// The list is sorted by priority, with the highest priority
// items first.
func All() (items []Item, err error) {

	if i, err := scriptItems(); err != nil {
		return nil, err
	} else {
		items = append(items, i...)
	}
	if i, err := fileItems(); err != nil {
		return nil, err
	} else {
		items = append(items, i...)
	}

	if config.Bool("update-rogu") {
		items = append(items, roguItem())
	}

	items = append(items, dotfileItem())
	sort.Slice(items, func(i, j int) bool {
		return items[i].Priority < items[j].Priority
	})
	return items, nil
}

type ItemType int

const (
	DotfileItem ItemType = iota
	RoguItem
	FileItem
	ScriptItem
)

type Item struct {
	Name        string
	Priority    int // Lower numbers are higher priority
	Type        ItemType
	IsInstalled func() (bool, error)
	Install     func() error
	Uninstall   func() error
	Update      func() error
}

func (i Item) String() string {
	return fmt.Sprintf(
		"Item{Name: %s, Priority: %d, Type: %s}",
		i.Name,
		i.Priority,
		i.Type,
	)
}

func dotfileItem() Item {
	return Item{
		Name:        "Dotfiles",
		Priority:    0,
		Type:        DotfileItem,
		IsInstalled: dotfiles.IsInstalled,
		Install:     dotfiles.Install,
		Update:      dotfiles.Sync,
	}
}
