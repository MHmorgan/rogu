//go:generate stringer -type=ItemType

// Package items implement the functionality for handling
// the user items defined in the config file.
//
// Install scripts are items which define shell
// scripts/commands to be run for installing, uninstalling,
// or updating items.
//
// Files are items which define files to be managed by Rogu,
// which will installer and keep them up to date.
package items

import (
	"fmt"
	"sort"
)

type itemsFactory func() ([]Item, error)

var itemsFactories []itemsFactory

// All returns a list of all items defined in the config.
//
// The list is sorted by priority, with the highest priority
// items first.
func All() (items []Item, err error) {
	for _, f := range itemsFactories {
		if ii, err := f(); err != nil {
			return nil, err
		} else {
			items = append(items, ii...)
		}
	}
	items = append(items, Rogu{})
	sort.Slice(items, func(i, j int) bool {
		return items[i].Priority() > items[j].Priority()
	})
	return items, nil
}

type ItemType int

const (
	DotfileItem ItemType = iota
	RoguItem
	FileItem
	ScriptItem
	TemplateItem
)

// Item

type Item interface {
	fmt.Stringer
	Name() string
	Priority() int // Higher numbers are higher priority.
	Type() ItemType
	Handlers() ItemHandlers
}

type Fn func() error
type BoolFn func() (bool, error)

type ItemHandlers struct {
	// Check runs any number of checks to determine if
	// the item is OK.
	//
	// The checks can be: is the item installed, is the
	// item up to date, etc.
	Check       Fn
	IsInstalled BoolFn
	Install     Fn
	Uninstall   Fn
	Update      Fn
}
