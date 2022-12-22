package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/items"
	log "github.com/mhmorgan/termlog"
	"os"
)

func init() {
	commands["doctor"] = &command{doctorFlags, doctor}
}

func doctorFlags(flags *flag.FlagSet) {
	flags.Usage = func() {
		fmt.Fprint(os.Stderr, doctorUsage)
		flags.PrintDefaults()
		os.Exit(2)
	}
}

func doctor(args []string) {
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
			log.Errorf("%v has no installation check", item.Name)
			continue
		}
		switch installed, err := item.IsInstalled(); {
		case err != nil:
			log.Errorf("%v IsInstalled: %v", item.Name, err)
		case !installed && item.Install == nil:
			log.Badf("%v is not installed and I don't know how to install it!", item.Name)
		case !installed:
			log.Emphf("Not installed: %v", item.Name)
		case installed:
			if item.Update != nil {
				log.Goodf("Installed & updated: %v", item.Name)
			} else {
				log.Goodf("Installed: %v", item.Name)
			}
		}
	}
}

const doctorUsage = `usage: rogu doctor [options] [filters...]

Diagnose your machine.

If filters are given only items matching the filters will
be checked.

Options:
`
