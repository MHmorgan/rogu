package cmd

import (
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/fs"
	log "github.com/mhmorgan/termlog"
	"github.com/spf13/cobra"
	"os"
)

var (
	cfgFile string
	verbose bool
)

func init() {
	cobra.OnInitialize(initConfig)
	pf := RootCmd.PersistentFlags()
	pf.StringVar(&cfgFile, "config", fs.RelHome(".rogu"), "config file")
	pf.BoolVarP(&verbose, "verbose", "v", false, "verbose output")
}

func initConfig() {
	f, err := os.Open(cfgFile)
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		if err := f.Close(); err != nil {
			log.Error(err)
		}
	}()
	if err := config.Load(f); err != nil {
		log.Fatal(err)
	}

	config.Set("verbose", verbose)
}

var RootCmd = &cobra.Command{
	Use:   "rogu",
	Short: "Rogu is my personal UNIX assistant.",
}
