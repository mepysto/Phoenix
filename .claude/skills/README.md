# Project skills

Third-party skills vendored for work on Phoenix. Before adding them, every
file was scanned for scripts, network fetches and instruction-injection
phrasing, and each SKILL.md entry file was read: they are plain Markdown
guidance, run no code and load nothing from the network at run time.
Update them by re-copying from the pinned source and re-reviewing the diff.

| Skill | Use | Source (commit) | Licence |
|---|---|---|---|
| vercel-react-best-practices | React/Next.js performance rules | vercel-labs/agent-skills `skills/react-best-practices` (1a2c79d) | MIT |
| vercel-composition-patterns | Component API and composition | vercel-labs/agent-skills `skills/composition-patterns` (1a2c79d) | MIT |
| review-animations | Review motion code (user-invoked) | emilkowalski/skills `skills/review-animations` (a81dbca) | MIT |
| animation-performance | Keep animations at 60 fps | emilkowalski/skills `skills/animation-performance` (a81dbca) | MIT |

Kept out on purpose: skills that duplicate the design and engineering
skills already available, collections of hundreds of skills (every
installed skill's description costs context in every session), skills
that inject content at session start, and skills that load their
instructions from a live URL.
