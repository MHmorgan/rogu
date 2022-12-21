package cmd

import (
	"fmt"
	"github.com/mhmorgan/rogu/items"
	log "github.com/mhmorgan/termlog"
	"github.com/spf13/cobra"
)

func init() {
	RootCmd.AddCommand(syncCmd)
}

var syncCmd = &cobra.Command{
	Use:     "sync",
	Aliases: []string{"s"},
	Short:   "Sync is a tool for syncing your system",
	Long: `Sync is a tool for syncing your system.

It installs and updates:
  - Rogu itself
  - Homebrew applications
  - Get-files`,

	Run: func(cmd *cobra.Command, args []string) {
		items_, err := items.All()
		if err != nil {
			log.Fatal(err)
		}
		for _, item := range items_ {
			if err := syncItem(item); err != nil {
				log.Fatal(err)
			}
		}
	},
}

func syncItem(item items.Item) error {
	if item.IsInstalled == nil {
		return fmt.Errorf("%s has no installation check", item.Name)
	}
	installed, err := item.IsInstalled()
	if err != nil {
		return err
	}
	if installed && item.Update != nil {
		log.Emphf("Updating %s (%d)", item.Name, item.Priority)
		return item.Update()
	}
	if !installed {
		if item.Install != nil {
			log.Emphf("Installing %s (%d)", item.Name, item.Priority)
			return item.Install()
		} else {
			log.Warnf("I don't know how to install %s", item.Name)
			return nil
		}
	}
	return nil
}
