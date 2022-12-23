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
	var itms []items.Item
	if ii, err := items.All(); err != nil {
		log.Fatal(err)
	} else {
		for _, item := range ii {
			if nameMatch(item.Name(), args) {
				itms = append(itms, item)
			}
		}
	}

	for _, item := range itms {
		h := item.Handlers()
		if h.Check == nil {
			log.Errorf("%v has no check", item.Name())
			continue
		}

		if err := h.Check(); err != nil {
			log.Badf("%v ... %v", item.Name(), err)
		} else {
			log.Goodf("%v ... OK", item.Name())
		}
	}
}

const doctorUsage = `usage: rogu doctor [options] [filters...]

Diagnose your machine.

If filters are given only items matching the filters will
be checked.

Options:
`
