package items

import (
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/git"
	"github.com/mhmorgan/rogu/utils"
	"path/filepath"
	"strings"
)

func init() {
	itemsFactories = append(itemsFactories, TemplateItems)
}

func TemplateItems() (items []Item, err error) {
	for name, val := range config.Get().Templates {
		item := Template{
			name:     name,
			priority: val.Priority,
			url:      val.Url,
			branch:   val.Branch,
		}
		if item.branch == "" {
			item.branch = config.DefaultBranch
		}
		items = append(items, item)
	}
	return
}

type Template struct {
	priority int
	name     string
	url      string
	branch   string
}

func (t Template) String() string {
	return fmt.Sprintf("Template %q", t.name)
}

func (t Template) Name() string {
	return t.name
}

func (t Template) Priority() int {
	return t.priority
}

func (t Template) Type() ItemType {
	return TemplateItem
}

func (t Template) Handlers() ItemHandlers {
	return ItemHandlers{
		Check:       t.checker(),
		IsInstalled: t.isInstalled(),
		Install:     t.installer(),
		Update:      t.updater(),
	}
}

func (t Template) Root() string {
	base := "." + strings.TrimSuffix(filepath.Base(t.url), ".git")
	home := utils.Home()
	return filepath.Join(home, base)
}

func (t Template) checker() Fn {
	return func() error {
		repo, err := git.Open(t.Root(), git.WithBranch(t.branch))
		if err != nil {
			return err
		}
		utils.Cd(t.Root())

		if files, err := repo.ModifiedFiles(); err != nil {
			return err
		} else if len(files) > 0 {
			return fmt.Errorf("%s has uncommitted changes", repo)
		}
		return nil
	}
}

func (t Template) installer() Fn {
	return func() error {
		if err := git.Clone(t.url, t.Root()); err != nil {
			return err
		}
		return nil
	}
}

func (t Template) updater() Fn {
	return func() error {
		repo, err := git.Open(t.Root(), git.WithBranch(t.branch))
		if err != nil {
			return err
		}
		utils.Cd(t.Root())
		return repo.Sync()
	}
}

func (t Template) isInstalled() BoolFn {
	return func() (bool, error) {
		return utils.PathExists(t.Root()), nil
	}
}
