package config

import (
	"gopkg.in/yaml.v3"
	"io"
)

var cfg Config

type Config struct {
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
	return yaml.NewDecoder(r).Decode(&cfg)
}

func Get() *Config {
	return &cfg
}
