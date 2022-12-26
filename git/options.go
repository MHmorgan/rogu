package git

type Option func(*Repo)

func WithCmd(cmd string) Option {
	return func(g *Repo) {
		g.cmd = cmd
	}
}

func WithBranch(branch string) Option {
	return func(g *Repo) {
		g.Branch = branch
	}
}
