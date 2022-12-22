package items

import "github.com/mhmorgan/rogu/config"

func roguItem() Item {
	cfg := config.Get()
	return Item{
		Name:        "Rogu",
		Priority:    -666,
		Type:        ScriptItem,
		IsInstalled: func() (bool, error) { return true, nil },
		Install:     fileInstaller(cfg.RoguUrl(), cfg.Rogu.Path, 0755),
		Update:      fileInstaller(cfg.RoguUrl(), cfg.Rogu.Path, 0755),
	}
}
