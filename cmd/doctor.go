package cmd

import (
	"github.com/mhmorgan/rogu/items"
	log "github.com/mhmorgan/termlog"
	"github.com/spf13/cobra"
)

func init() {
	RootCmd.AddCommand(doctorCmd)
}

var doctorCmd = &cobra.Command{
	Use:     "doctor",
	Aliases: []string{"d"},
	Short:   "Doctor is a tool for diagnosing common problems with your Rogu installation",
	Long: `Doctor is a tool for diagnosing common problems.

Run an sanity check of everything Rogu knows about on the
system. This is mostly a passive action, but not completely.

The optional FILTER allows filtering on which sanity checks
are performed, selecting on title.

When --fix is given Rogu tries to fix any issues as soon as
it is encountered, if he knows how.`,

	Run: func(cmd *cobra.Command, args []string) {
		items_, err := items.All()
		if err != nil {
			log.Fatal(err)
		}

		for _, item := range items_ {
			if item.IsInstalled == nil {
				log.Errorf("%s has no installation check", item.Name)
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
	},
}
