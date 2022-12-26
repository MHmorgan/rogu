package git

type ErrNotInstalled struct {
	name string
}

func (e ErrNotInstalled) Error() string {
	return "repository not installed: " + e.name
}
