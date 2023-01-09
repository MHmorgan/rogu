Rogu
====

Roger's weird offspring and my personal UNIX assistant.


TODO
----

* Implement `release` command:
  Create a new release+tag on GitHub, and upload release
  assets automatically. Use GitHub CLI as library?

* Use [github.com/cli/go-gh](https://pkg.go.dev/github.com/cli/go-gh)
  for interract with github releases and assets.  
  See [endpoints](https://docs.github.com/en/rest/overview/endpoints-available-for-github-apps).

* Use a single item for all templates.
  Store templates as an array of URL's in the config.

* Rewrite cli with cobra

* Write installation script

* Make default behoviour, when calling Rogu without arguments,
  to perform the doctor functionality.
  Maybe something other than doctor as well? Fix stuff?

