package items

import (
	"github.com/mhmorgan/rogu/config"
)

const roguItemName = "Rogu"

type Rogu struct{}

func (r Rogu) String() string {
	return roguItemName
}

func (r Rogu) Name() string {
	return roguItemName
}

func (r Rogu) Priority() int {
	return 666
}

func (r Rogu) Type() ItemType {
	return RoguItem
}

func (r Rogu) Handlers() ItemHandlers {
	cfg := config.Get()
	h := ItemHandlers{
		Check:       fileChecker(roguItemName, cfg.RoguUrl(), cfg.Rogu.Path),
		IsInstalled: func() (bool, error) { return true, nil },
		Install:     fileInstaller(cfg.RoguUrl(), cfg.Rogu.Path, 0755),
		Update:      fileInstaller(cfg.RoguUrl(), cfg.Rogu.Path, 0755),
	}

	return h
}
