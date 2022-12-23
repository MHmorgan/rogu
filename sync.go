package main

import (
	"flag"
	"fmt"
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
	var itms []items.Item
	if ii, err := items.All(); err != nil {
		log.Fatal(err)
	} else {
		for _, item := range ii {
			if !(updateRogu || item.Type() != items.RoguItem) {
				continue
			}
			if nameMatch(item.Name(), args) {
				itms = append(itms, item)
			}
		}
	}

	for _, item := range itms {
		h := item.Handlers()
		if h.IsInstalled == nil {
			log.Fatalf("%s has no installation check", item.Name())
		}
		installed, err := h.IsInstalled()
		if err != nil {
			log.Fatal(err)
		}

		if !installed {
			if h.Install != nil {
				log.Emphf("Installing %s", item.Name())
				err = h.Install()
			} else {
				log.Warnf("I don't know how to install %s", item.Name())
			}
		} else if h.Update != nil {
			log.Infof("Updating %s", item.Name())
			err = h.Update()
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
