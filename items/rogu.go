package items

import (
	"github.com/mhmorgan/rogu/config"
)

const roguItemName = "Rogu"

type roguItem struct{}

func (r roguItem) String() string {
	return roguItemName
}

func (r roguItem) Name() string {
	return roguItemName
}

func (r roguItem) Priority() int {
	return 666
}

func (r roguItem) Type() ItemType {
	return RoguItem
}

func (r roguItem) Handlers() ItemHandlers {
	cfg := config.Get()
	h := ItemHandlers{
		Check:       fileChecker(roguItemName, cfg.RoguUrl(), cfg.Rogu.Path),
		IsInstalled: func() (bool, error) { return true, nil },
		Install:     fileInstaller(cfg.RoguUrl(), cfg.Rogu.Path, 0755),
		Update:      fileInstaller(cfg.RoguUrl(), cfg.Rogu.Path, 0755),
	}

	return h
}
