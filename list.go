package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/git"
	log "github.com/mhmorgan/termlog"
	"os"
)

func init() {
	commands["list"] = &command{listFlags, list}
}

func listFlags(flags *flag.FlagSet) {
	flags.Usage = func() {
		fmt.Fprint(os.Stderr, listUsage)
		flags.PrintDefaults()
		os.Exit(2)
	}
}

func list(args []string) {
	repo, err := git.DotfilesRepo()
	if err != nil {
		log.Fatal(err)
	}
	files, err := repo.Files()
	if err != nil {
		log.Fatal(err)
	}
	for _, file := range files {
		fmt.Println(file)
	}
}

const listUsage = `usage: rogu list

List all dotfiles

Options:
`
