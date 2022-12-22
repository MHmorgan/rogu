package dotfiles

// TODO Use github.com/go-git/go-git/v5
// TODO Edit dotfiles through rogu

import (
	"fmt"
	"github.com/mhmorgan/rogu/fs"
	"github.com/mhmorgan/rogu/sh"
	log "github.com/mhmorgan/termlog"
	"strings"
)

var (
	Root   string
	Repo   = "https://github.com/MHmorgan/dotfiles-mac.git"
	Branch = "main"
)

func init() {
	Root = fs.RelHome(".dotfiles")
}

// IsInstalled returns true if the dotfiles repository is installed.
func IsInstalled() (bool, error) {
	return fs.Exists(Root), nil
}

// IsDirty returns true if the dotfiles repository has uncommitted changes.
func IsDirty() bool {
	out, _, err := sh.Exec(gitCode("status --short"))
	if err != nil {
		log.Fatal(err)
	}
	return out.Len() > 0
}

// Files returns the list of dotfiles in the dotfiles repository.
func Files() ([]string, error) {
	// ls-tree won't work if we're not home.
	// Since this is a public function this must be handled here.
	if err := fs.CdHome(); err != nil {
		return nil, err
	}

	out, _, err := sh.Exec(gitCode("ls-tree -r --name-only %v", Branch))
	if err != nil {
		return nil, fmt.Errorf("git ls-tree: %w", err)
	}
	return strings.Split(out.String(), "\n"), nil
}

func Install() error {
	if err := fs.CdHome(); err != nil {
		return err
	}
	if err := sh.Runf("git clone --bare %s %s", Repo, Root); err != nil {
		return err
	}
	// Backup existing dotfiles
	files, err := Files()
	if err != nil {
		return err
	}
	for _, file := range files {
		if fs.Exists(file) {
			if err = fs.Backup(file); err != nil {
				return err
			}
		}
	}
	// Dotfiles setup
	gitCalls := []string{
		"checkout " + Branch,
		"config advice.addIgnoredFile false",
		"config branch." + Branch + ".remote origin",
		"config branch." + Branch + ".merge refs/heads/" + Branch,
	}
	for _, args := range gitCalls {
		code := gitCode(args)
		if err := sh.Run(code); err != nil {
			return err
		}
	}
	return nil
}

func Update() error {
	if err := fs.CdHome(); err != nil {
		return err
	}
	if IsDirty() {
		return fmt.Errorf("dotfiles repository is dirty")
	}
	code := gitCode("pull --rebase origin %s", Branch)
	return sh.Run(code)
}

func gitCode(args string, a ...any) string {
	prefix := fmt.Sprintf("git --git-dir=%s --work-tree=%s ", Root, fs.Home())
	if len(a) == 0 {
		return prefix + args
	}
	return prefix + fmt.Sprintf(args, a...)
}
