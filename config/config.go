package config

import (
	log "github.com/mhmorgan/termlog"
	"gopkg.in/yaml.v3"
	"io"
	"path"
)

var (
	cfg        Config
	roguBinary string
	values     = make(map[any]any)
)

type Config struct {
	RoguUrlDir string `yaml:"rogu_url_dir"`
	RoguBinary string `yaml:"-"`

	Scripts map[string]struct {
		Priority  int
		Check     string
		Install   string
		Uninstall string
		Update    string
	}

	Files map[string]struct {
		Priority    int
		Source      string
		Destination string
		Mode        int
	}
}

func Load(r io.Reader) error {
	if err := yaml.NewDecoder(r).Decode(&cfg); err != nil {
		return err
	}
	cfg.RoguBinary = roguBinary
	return nil
}

func Get() *Config {
	return &cfg
}

func (c *Config) RoguUrl() string {
	if c.RoguUrlDir == "" {
		log.Fatal("rogu_url_dir not set in config")
	}
	return path.Join(c.RoguUrlDir, roguBinary)
}

func Set(key, val any) {
	values[key] = val
}

func Value(key any) any {
	return values[key]
}

func Bool(key any) bool {
	if val, ok := values[key].(bool); ok {
		return val
	}
	return false
}
