package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/dotfiles"
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
	files, err := dotfiles.Files()
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
