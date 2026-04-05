## todo

- better support for ai-less e2e testing
  - skill
  - mention in readme
  - reproducibility?
  - cleanup?

- proxy stuff
  - highlight that tool works both from host and from vm
  - rm obsessive transparent proxy mentions from docs

- installer
  - uvx as recommended option, rm pip
  - rename default init action to smth more scary to use (available for users who want to override/edit but not recommended for all)
  - auto bundle skills on installation
  - override command name in skills on local installation
  - in install skill highlight that vagrantfile may need to be edited to work with particular host/networking
  - default dir .qt-ai-dev-tools/ for workspace and tooling

- proper configuration: env vars, config files - for all long-term persistent stuff. eg cfg goes into worktree init to render vagrant files

- rewrite cli api
  - add `-h` alias to --help

- rename to qt-dev-tools
- mark that it is mostly for python+qt, smth may work with cpp+qt but never tested
- mark that rn implementation only for x11 mode
- use it as accessibility tool?
- potential for non-qt apps?
- record screen?
- live screen stream?
- live intreractive connection like vnc? will virt-manager work?
