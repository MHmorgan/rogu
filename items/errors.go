package items

import "fmt"

type NotInstalledError struct {
	Name string
}

func (e NotInstalledError) Error() string {
	return fmt.Sprintf("%s is not installed", e.Name)
}

type NoInstallerError struct {
	Name string
}

func (e NoInstallerError) Error() string {
	return fmt.Sprintf("%s has no installer", e.Name)
}

type NoInstalledCheckError struct {
	Name string
}

func (e NoInstalledCheckError) Error() string {
	return fmt.Sprintf("%s has no installed checker", e.Name)
}
