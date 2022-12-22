package sh

import (
	"bytes"
	"fmt"
	"github.com/commander-cli/cmd"
	"github.com/mhmorgan/rogu/config"
	"os"
)

// Run runs a shell command which will print stdout and stderr
// to the terminal.
func Run(s string) error {
	if config.Bool("verbose") {
		s = "set -x; " + s
	}
	c := cmd.NewCommand(s, cmd.WithCustomStdout(os.Stdout), cmd.WithCustomStderr(os.Stderr))
	if err := c.Execute(); err != nil {
		return err
	}
	if c.ExitCode() != 0 {
		return fmt.Errorf("exit code %d", c.ExitCode())
	}
	return nil
}

// Runf runs a shell command which will print stdout and stderr
// to the terminal.
func Runf(format string, a ...interface{}) error {
	return Run(fmt.Sprintf(format, a...))
}

// Exec runs a shell command and returns the stdout and stderr
// combined into a single buffer.
func Exec(s string) (b bytes.Buffer, code int, err error) {
	c := cmd.NewCommand(s, cmd.WithCustomStdout(&b), cmd.WithCustomStderr(&b))
	err = c.Execute()
	code = c.ExitCode()
	return
}

// Execf runs a shell command and returns the stdout and stderr
// combined into a single buffer.
func Execf(format string, a ...interface{}) (bytes.Buffer, int, error) {
	return Exec(fmt.Sprintf(format, a...))
}
