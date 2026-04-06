## todo

### backlog

#### soon

- better support for ai-less e2e testing
  - skill
  - mention in readme
  - reproducibility?
  - cleanup?

- installer
  - uvx as recommended option, rm pip
  - update available warning at top of cli output
  - bake version/commit on publish into build
  - rename default init action to smth more scary to use like `install-and-own` (available for users who want to override/edit but not recommended for all), require confirmation like `--yes-I-will-maintain-it`
  - auto bundle skills on local installation (rm default generic skills? install skills into dir and ln global skill locations like .calude/skills/? integraion with npx skills for simplification?)
  - override command name in skills on local installation
  - in installation skill highlight that vagrantfile may need to be edited to work with particular host/networking
  - default dir .qt-ai-dev-tools/ for workspace and tooling

- docs
  - mark in docs/skills that it is mostly for python+qt, smth may work with cpp+qt but never tested
  - mark that rn implementation only for x11 no wayland
  - "proxy" mentions
    - highlight that tool works both from host and from vm
    - rm obsessive "transparent proxy" mentions from docs

- cli api
  - rewrite: make it more logical, simple and structured
  - support config loading
  - allow to put -v/--dry-run anywhere? like global options? Is it good pattern? idk
  - --dry-run should be auto -v
  - do we need -v vs -vv? maybe leave only one?
  - print short helper instructions for some commands
    - workspace init: suggest to edit vagrantfile/provision script

- proper configuration: env vars, config files - for all long-term persistent stuff. eg cfg goes into worktree init to render vagrant files

- rename to qt-dev-tools
- rewrite tests launching: move responsibility of proper tests launch environment (vm/host etc) from makefile to pytest/config/pyproj/python helpers etc. Ensure each test action produces exactly one pytest run with all summarization at bottom, not multiple runs with logs on top of each other

#### later

- record screen?
- live screen stream?
- live intreractive connection like vnc? will virt-manager work? only for vm or for docker too?

### future thoughts
- potential use it as accessibility tool?
- potential for non-qt apps?
- more AT-SPI coverage
