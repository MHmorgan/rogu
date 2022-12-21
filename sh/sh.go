package sh

import (
	"bytes"
	"fmt"
	"github.com/commander-cli/cmd"
	"os"
)

// Run runs a shell command which will print stdout and stderr
// to the terminal.
func Run(code string) error {
	return cmd.NewCommand(
		code,
		cmd.WithCustomStdout(os.Stdout),
		cmd.WithCustomStderr(os.Stderr),
	).Execute()
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
