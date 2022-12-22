package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/sh"
	"github.com/mhmorgan/rogu/utils"
	log "github.com/mhmorgan/termlog"
	"os"
	"path"
)

func init() {
	commands["boilerplates"] = &command{boilerplatesFlags, boilerplates}
}

func boilerplatesFlags(flags *flag.FlagSet) {
	flags.Usage = func() {
		fmt.Fprint(os.Stderr, boilerplatesUsage)
		flags.PrintDefaults()
		os.Exit(2)
	}
}

func boilerplates(args []string) {
	base := config.Get().Boilerplates.UrlDir

	var url string
	switch {
	case len(args) == 0:
		url = path.Join(base, "meta/filelist.txt")
	default:
		url = path.Join(base, args[0])
	}

	if err := getBoilerplate(url); err != nil {
		log.Fatal(err)
	}
}

func getBoilerplate(url string) error {
	resp, ok, err := utils.UrlExists(url)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("file not found: %v (response %d)", url, resp)
	}

	return sh.Runf("curl -sSL %v", url)
}

const boilerplatesUsage = `usage: rogu boilerplates [options] [FILE]

Download a boilerplate file.

Options:
`
