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
  - uvx as recommended option
  - rename default init action to smth more scary to use (available for users who want to override/edit but not recommended for all)
  - auto bundle skills on installation
  - override command name in skills on local installation
- rewrite cli api
- rename to qt-dev-tools
- mark that it is mostly for python+qt, smth may work with cpp+qt but never tested
- mark that rn implementation only for x11 mode
- use it as accessibility tool?
- potential for non-qt apps?
- backlog
  - wayland support
  
## propmpts

---

okay. now your goal is to spawn couple of triage agents, with different priorities/logic/focus, feed them all important docs and context and compare their suggestions. than create a fix plan and todo, proceed, fix everything that you will pick in triage. 

scope: entire project
type of issues to fix: real bugs, typing/arch problems, tests coverage, uncovered features, docs
max priority: features that are not yet properly tested or that are skipped in tests. 90% chance that they don't work at all
low priority: refactorings that do not relate to other issues or problems, security problems (not really applicable to this local dev tool working in vm)
effort level: high but not "max-effort-clean-everything-possible"

your goal is to increase count of tested/working features, prevent potential bugs/edge cases. with current project state there are lots of feature that are poorly covered and broken due to this because no real manual testing was done. better to cover everything important with e2e tests. this will show what is broken and help to make it work

you are free to make architectural descisions, update vm provisioning and so on

after tis point, your goal is to finish this work to result. don't ask me additional questions, rely on other docs and philosophies when making descisions

extensively use subagents and skills

---

@docs/ROADMAP.md @CLAUDE.md @README.md 

run complex project review and audit, check implementation. some bugs exist, some e2e tests fail or are skipped.

use all relevant skills: testing python code, writing python code, qt skill

classify issues, research potential solutions  - arch-level for complex issues, fixes for small ones

run separate test cases verifier agent. it should also load py testing skill and check if implemented test cases re really testing smth important not just produce green check marks. also it should think if any important test cases are missing additionally to what is already coverd by your report.

create final docs/reports/xxx doc

---

AD HOC TESTING FIRST BEFORE FULL COMMITMENT!!!

---

arch design skill
