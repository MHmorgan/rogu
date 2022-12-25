package items

import "github.com/mhmorgan/rogu/dotfiles"

const dotfilesItemName = "Dotfiles"

type dotfilesItem struct{}

func (d dotfilesItem) String() string {
	return dotfilesItemName
}

func (d dotfilesItem) Name() string {
	return dotfilesItemName
}

func (d dotfilesItem) Priority() int {
	return 60
}

func (d dotfilesItem) Type() ItemType {
	return DotfileItem
}

func (d dotfilesItem) Handlers() ItemHandlers {
	return ItemHandlers{
		Check:       dotfiles.Check,
		IsInstalled: dotfiles.IsInstalled,
		Install:     dotfiles.Install,
		Update:      dotfiles.Sync,
	}
}
