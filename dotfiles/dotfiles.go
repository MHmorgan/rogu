package dotfiles

import (
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/sh"
	"github.com/mhmorgan/rogu/utils"
	log "github.com/mhmorgan/termlog"
	"strings"
)

var (
	Root   string
	Repo   = "https://github.com/MHmorgan/dotfiles-mac.git"
	Branch = "main"
)

func init() {
	Root = utils.RelHome(".dotfiles")
}

// IsInstalled returns true if the dotfiles repository is installed.
func IsInstalled() (bool, error) {
	return utils.PathExists(Root), nil
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
	if err := utils.CdHome(); err != nil {
		return nil, err
	}

	out, _, err := sh.Exec(gitCode("ls-tree -r --name-only %v", Branch))
	if err != nil {
		return nil, fmt.Errorf("git ls-tree: %w", err)
	}
	return strings.Split(out.String(), "\n"), nil
}

func Install() error {
	if err := utils.CdHome(); err != nil {
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
		if utils.PathExists(file) {
			if err = utils.Backup(file); err != nil {
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

func Sync() error {
	if err := utils.CdHome(); err != nil {
		return err
	}

	var commit, push string
	if IsDirty() {
		commit = gitCode("commit -am 'Sync dotfiles' ; ")
		push = gitCode("push origin %s ; ", Branch)
	}

	pull := gitCode("pull --rebase origin %s ; ", Branch)
	return sh.Runf("%s%s%s", commit, pull, push)
}

func Commit(path string) error {
	if err := utils.CdHome(); err != nil {
		return err
	}

	add := gitCode("add %s ; ", path)
	commit := gitCode("commit -m 'Update %s' ; ", path)

	return sh.Runf("%s%s", add, commit)
}

func Push() error {
	if err := utils.CdHome(); err != nil {
		return err
	}
	cfg := config.Get()
	push := gitCode("push origin %s", cfg.Dotfiles.Branch)
	return sh.Run(push)
}

func Edit(name, editor string) error {
	if err := utils.CdHome(); err != nil {
		return err
	}
	return sh.Runf("%s %s", editor, name)
}

func gitCode(args string, a ...any) string {
	prefix := fmt.Sprintf("git --git-dir=%s --work-tree=%s ", Root, utils.Home())
	if len(a) == 0 {
		return prefix + args
	}
	return prefix + fmt.Sprintf(args, a...)
}
