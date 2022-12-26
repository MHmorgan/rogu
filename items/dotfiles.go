package items

import (
	"errors"
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/git"
	"github.com/mhmorgan/rogu/utils"
	"os"
)

const (
	dotfilesItemName = "Dotfiles"
)

func init() {
	itemsFactories = append(itemsFactories, func() ([]Item, error) {
		return []Item{DotfilesItem()}, nil
	})
}

func DotfilesItem() Item {
	cfg := config.Get()
	item := Dotfiles{
		root:   os.ExpandEnv("$HOME/.dotfiles"),
		url:    cfg.Dotfiles.Url,
		branch: cfg.Dotfiles.Branch,
	}
	if item.branch == "" {
		item.branch = config.DefaultBranch
	}
	return item
}

type Dotfiles struct {
	root   string
	url    string
	branch string
}

func (d Dotfiles) String() string {
	return dotfilesItemName
}

func (d Dotfiles) Name() string {
	return dotfilesItemName
}

func (d Dotfiles) Priority() int {
	return 60
}

func (d Dotfiles) Type() ItemType {
	return DotfileItem
}

func (d Dotfiles) Handlers() ItemHandlers {
	return ItemHandlers{
		Check:       d.checker(),
		IsInstalled: d.isInstalled(),
		Install:     d.installer(),
		Update:      d.updater(),
	}
}

func (d Dotfiles) checker() Fn {
	return func() error {
		repo, err := git.DotfilesRepo()
		if err != nil {
			return err
		}
		utils.CdHome()

		files, err := repo.Files()
		if err != nil {
			return err
		}
		for _, file := range files {
			if !utils.PathExists(file) {
				return fmt.Errorf("dotfile %q is missing", file)
			}
		}

		if files, err := repo.ModifiedFiles(); err != nil {
			return err
		} else if len(files) > 0 {
			return errors.New("dotfiles repository has uncommitted changes")
		}
		return nil
	}
}

func (d Dotfiles) installer() Fn {
	return func() error {
		if err := git.CloneBare(d.url, d.root); err != nil {
			return err
		}
		repo, err := git.DotfilesRepo()
		if err != nil {
			return err
		}
		utils.CdHome()

		// Backup existing dotfiles
		files, err := repo.Files()
		if err != nil {
			return err
		}
		for _, file := range files {
			if utils.PathExists(file) {
				if err = utils.Backup(file); err != nil {
					return err
				}
			}
		}

		if err := repo.Run("checkout %s", d.branch); err != nil {
			return err
		}
		_ = repo.SetConfig("advice.addIgnoredFile", "false")
		_ = repo.SetConfig("branch.{{ .Branch }}.remote", "origin")
		_ = repo.SetConfig("branch.{{ .Branch }}.merge", "refs/heads/{{ .Branch }}")
		return nil
	}
}

func (d Dotfiles) updater() Fn {
	return func() error {
		repo, err := git.DotfilesRepo()
		if err != nil {
			return err
		}
		utils.CdHome()
		return repo.Sync()
	}
}

func (d Dotfiles) isInstalled() BoolFn {
	return func() (bool, error) {
		return utils.PathExists(d.root), nil
	}
}
