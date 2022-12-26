Rogu
====

Roger's weird offspring and my personal UNIX assistant.


TODO
----

* Implement `release` command:
  Create a new release+tag on GitHub, and upload release
  assets automatically. Use GitHub CLI as library?

* Implement `init <lang>` command.
    * Run `git init` in the current directory.
    * `<lang>` defines the git template to use for the
      repository, based on programming language.
      Use `git init --template`.
    * Store git template repositories in home directory, in
      hidden folders managed by rogu.
    * Prompt the user for name and email and automatically
      configure git, `git config user.name/email`.
    * Add template item for managing items.
