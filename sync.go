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

	var err error
	var items_ []items.Item
	if len(args) == 0 {
		items_, err = items.All()
	} else {
		items_, err = items.Filtered(args...)
	}
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
				log.Emphf("Installing %s", item.Name)
				err = item.Install()
			} else {
				log.Warnf("I don't know how to install %s", item.Name)
			}
		} else if item.Update != nil {
			log.Emphf("Updating %s", item.Name)
			err = item.Update()
		}
		if err != nil {
			log.Fatal(err)
		}
	}
}

const syncUsage = `usage: rogu sync [options] [filters...]

Install and update all of Rogu's items.

If filters are given only items matching the filters will
be synced.

Options:
`
