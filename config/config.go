package config

import (
	log "github.com/mhmorgan/termlog"
	"gopkg.in/yaml.v3"
	"io"
	"os"
	"path"
)

var (
	cfg        Config
	roguBinary string
	values     = make(map[any]any)
)

type Config struct {
	Rogu struct {
		UrlDir string `yaml:"url_dir"`
		Binary string `yaml:"-"`
		Path   string
	}

	Dotfiles struct {
		Repo   string
		Branch string
	}

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
	cfg.Rogu.Binary = roguBinary
	return nil
}

func Loadf(path string) error {
	f, err := os.Open(path)
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		if err := f.Close(); err != nil {
			log.Error(err)
		}
	}()
	return Load(f)
}

func Get() *Config {
	return &cfg
}

func (c *Config) RoguUrl() string {
	if c.Rogu.UrlDir == "" {
		log.Fatal("rogu_url_dir not set in config")
	}
	return path.Join(c.Rogu.UrlDir, roguBinary)
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
