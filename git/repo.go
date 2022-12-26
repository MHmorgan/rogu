package git

import (
	"bytes"
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/sh"
	"github.com/mhmorgan/rogu/utils"
	"os"
	"strings"
	"text/template"
)

type Repo struct {
	Root   string
	Branch string
	cmd    string
}

func Open(root string, options ...Option) (r Repo, err error) {
	if !utils.PathExists(root) {
		return r, fmt.Errorf("%s: %w", root, os.ErrNotExist)
	}
	r = Repo{
		Root:   root,
		Branch: "main",
		cmd:    "git",
	}
	for _, option := range options {
		option(&r)
	}
	return r, nil
}

func DotfilesRepo() (Repo, error) {
	cfg := config.Get()
	root := os.ExpandEnv("$HOME/.dotfiles")
	cmd := fmt.Sprintf("git --git-dir=%s --work-tree=%s ", root, utils.Home())
	return Open(root, WithBranch(cfg.Dotfiles.Branch), WithCmd(cmd))
}

func Clone(repo, root string) error {
	return sh.Runf("git clone %s %s", repo, root)
}

func CloneBare(repo, root string) error {
	return sh.Runf("git clone --bare %s %s", repo, root)
}

// Files returns a list of files tracked by the repository.
//
// For this to work you must be in the work-tree of the
// repository.
func (r Repo) Files() (files []string, err error) {
	out, _, err := sh.Execf("%s ls-files", r.cmd)
	if err != nil {
		return nil, fmt.Errorf("git ls-files: %w", err)
	}

	for _, file := range strings.Split(out.String(), "\n") {
		file = strings.TrimSpace(file)
		if file != "" {
			files = append(files, file)
		}
	}
	return
}

func (r Repo) IsDirty() (bool, error) {
	out, _, err := sh.Execf("%s status --short", r.cmd)
	if err != nil {
		return false, fmt.Errorf("git status: %w", err)
	}
	return out.Len() > 0, nil
}

// ModifiedFiles returns a list of modified and added files.
func (r Repo) ModifiedFiles() (files []string, err error) {
	out, _, err := sh.Execf("%s ls-files --modified", r.cmd)
	if err != nil {
		return nil, fmt.Errorf("git ls-files: %w", err)
	}
	for _, line := range strings.Split(out.String(), "\n") {
		if line == "" {
			continue
		}
		files = append(files, line)
	}
	return
}

func (r Repo) Sync() error {
	var commit, push string
	if files, err := r.ModifiedFiles(); err != nil {
		return err
	} else if len(files) > 0 {
		s := strings.Join(files, " ")
		commit = fmt.Sprintf("%s commit -m 'Updating %s' -- %s ; ", r.cmd, s, s)
		push = fmt.Sprintf("%s push origin %s ; ", r.cmd, r.Branch)
	}

	pull := fmt.Sprintf("%s pull --rebase origin %s ; ", r.cmd, r.Branch)
	return sh.Runf("%s%s%s", commit, pull, push)
}

func (r Repo) Config(key string) (string, error) {
	out, _, err := r.Exec("config %s", key)
	if err != nil {
		return "", fmt.Errorf("git config: %w", err)
	}
	return out.String(), nil
}

func (r Repo) SetConfig(key, value string) error {
	return r.Run("config %s %s", key, value)
}

func (r Repo) Run(s string, args ...any) error {
	s, err := r.fmt(s)
	if err != nil {
		return err
	}
	return sh.Runf(s, args...)
}

func (r Repo) Exec(s string, args ...any) (b bytes.Buffer, code int, err error) {
	s, err = r.fmt(s)
	if err != nil {
		return
	}
	return sh.Execf(s, args...)
}

func (r Repo) fmt(s string) (string, error) {
	tmpl, err := template.New("git").Parse(s)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, r); err != nil {
		return "", err
	}
	return r.cmd + " " + buf.String(), nil
}
