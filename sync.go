package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/items"
	log "github.com/mhmorgan/termlog"
	"os"
)

var (
	updateRogu bool
)

func init() {
	commands["sync"] = &command{syncFlags, sync}
}

func syncFlags(flags *flag.FlagSet) {
	flags.Usage = func() {
		fmt.Fprint(os.Stderr, syncUsage)
		flags.PrintDefaults()
		os.Exit(2)
	}
	flags.BoolVar(&updateRogu, "rogu", false, "sync rogu himself")
}

func sync(args []string) {
	config.Set("update-rogu", updateRogu)

	items_, err := items.All()
	if err != nil {
		log.Fatal(err)
	}

	for _, item := range items_ {
		if item.IsInstalled == nil {
			log.Fatalf("%s has no installation check", item.Name)
		}
		installed, err := item.IsInstalled()
		if err != nil {
			log.Fatal(err)
		}

		if !installed {
			if item.Install != nil {
				log.Emphf("Installing %s (%d)", item.Name, item.Priority)
				err = item.Install()
			} else {
				log.Warnf("I don't know how to install %s", item.Name)
			}
		} else if item.Update != nil {
			log.Emphf("Updating %s (%d)", item.Name, item.Priority)
			err = item.Update()
		}
		if err != nil {
			log.Fatal(err)
		}
	}
}

const syncUsage = `usage: rogu sync [options]

Install and update all of Rogu's items.

Options:
`
