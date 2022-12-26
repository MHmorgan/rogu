package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/git"
	"github.com/mhmorgan/rogu/items"
	"github.com/mhmorgan/rogu/utils"
	log "github.com/mhmorgan/termlog"
	"os"
)

var (
	listTemplates bool
)

func init() {
	commands["init"] = &command{initFlags, init_}
}

func initFlags(flags *flag.FlagSet) {
	flags.Usage = func() {
		fmt.Fprint(os.Stderr, initUsage)
		flags.PrintDefaults()
		os.Exit(2)
	}
	flags.BoolVar(&listTemplates, "l", false, "list available templates")
}

func init_(args []string) {
	itms, err := items.TemplateItems()
	if err != nil {
		log.Fatal(err)
	}

	if listTemplates {
		for _, item := range itms {
			fmt.Println(item.Name())
		}
		return
	}

	switch len(args) {
	case 0:
		log.Fatal("no template language specified")
	case 1:
		// ok
	default:
		log.Fatal("too many arguments")
	}

	if utils.PathExists(".git") {
		log.Fatal("already in a git repository")
	}

	var tmplDir string
	for _, itm := range itms {
		tmpl := itm.(items.Template)
		if tmpl.Name() == args[0] {
			tmplDir = tmpl.Root()
			break
		}
	}
	if tmplDir == "" {
		log.Fatalf("no template found for %q", args[0])
	}

	if err := git.InitTemplate(tmplDir); err != nil {
		log.Fatal(err)
	}
}

const initUsage = `usage: rogu init [options] <lang>

Initialize a new git repository in the current directory.

Options:
`
