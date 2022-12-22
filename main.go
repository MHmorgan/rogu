package main

import (
	"github.com/mhmorgan/rogu/cmd"
	log "github.com/mhmorgan/termlog"
)

// TODO Rewrite to use flag and custom commands instead of cobra
func main() {
	if err := cmd.RootCmd.Execute(); err != nil {
		log.Fatal(err)
	}
}
