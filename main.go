package main

import (
	"flag"
	"fmt"
	"github.com/mhmorgan/rogu/config"
	"github.com/mhmorgan/rogu/utils"
	log "github.com/mhmorgan/termlog"
	"os"
	"strings"
)

var (
	verbose bool

	defaultCfgFile = utils.RelHome(".rogu")
)

type command struct {
	flags func(*flag.FlagSet)
	run   func([]string)
}

var commands = make(map[string]*command)

func main() {
	help := &command{}
	commands["help"] = help
	commands["-h"] = help
	commands["--help"] = help

	// Find command.
	var name string
	if len(os.Args) >= 2 {
		name = findCommand(os.Args[1])
	}
	if name == "" {
		fmt.Fprint(os.Stderr, mainUsage)
		if len(os.Args) >= 2 {
			log.Errorf("Unknown command %q", os.Args[1])
		}
		os.Exit(2)
	}
	if commands[name] == help {
		fmt.Fprint(os.Stderr, mainUsage)
		os.Exit(0)
	}

	// Parse flags.
	flags := flag.NewFlagSet(name, flag.ExitOnError)
	flags.BoolVar(&verbose, "v", false, "verbose output")
	commands[name].flags(flags)
	if err := flags.Parse(os.Args[2:]); err != nil {
		log.Fatal(err)
	}

	// Initialize config.
	cfgFile, ok := os.LookupEnv("ROGU_CONFIG")
	if !ok {
		cfgFile = defaultCfgFile
	}
	if err := config.Loadf(cfgFile); err != nil {
		log.Fatal(err)
	}
	config.Set("verbose", verbose)

	commands[name].run(flags.Args())
}

func findCommand(s string) (name string) {
	if s == "" {
		return
	}
	for key := range commands {
		if key == s {
			return key
		}
		if len(key) > len(s) && key[:len(s)] == s {
			if name != "" {
				log.Fatalf("Ambiguous command %q (could be %q or %q)", s, name, key)
			}
			name = key
		}
	}
	return
}

func nameMatch(name string, ss []string) bool {
	if len(ss) == 0 {
		return true
	}
	name = strings.ToLower(name)
	for _, s := range ss {
		s = strings.ToLower(s)
		if strings.Contains(name, s) {
			return true
		}
	}
	return false
}

const mainUsage = `usage: rogu <command> [arguments]

 ____                   
|  _ \ ___   __ _ _   _ 
| |_) / _ \ / _' | | | |
|  _ < (_) | (_| | |_| |
|_| \_\___/ \__, |\__,_|
            |___/       
 	
Rogu is my personal UNIX assistant.

The commands are:

    boilerplate  download a boilerplate file
    doctor       diagnose your machine
    help         show this help
    init         initialize a new git repository
    list	     list all dotfiles
    sync         install and update Rogu's items

Environment variables:

    ROGU_CONFIG  Path to config file (default: ~/.rogu)
`
