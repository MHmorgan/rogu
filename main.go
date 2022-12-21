package main

import (
	"github.com/mhmorgan/rogu/cmd"
	log "github.com/mhmorgan/termlog"
)

func main() {
	if err := cmd.RootCmd.Execute(); err != nil {
		log.Fatal(err)
	}
}
