# Dashboard

DevDoctor launches into an interactive Textual dashboard by default when attached to a terminal.

## Pages

- Health Overview: score, pass/warning/failure counts, last scan, and recommendations.
- System: CPU, RAM, GPU, disk, kernel, distribution, hostname, and architecture.
- Development Tools: cards for Git, Docker, Podman, Python, Node.js, npm, pnpm, Bun, Rust, Cargo, Go, Java, Terraform, Helm, kubectl, and GitHub CLI.
- Containers: focused Docker and Podman view.
- Networking: internet, DNS, and GitHub reachability.
- Security: safe local posture signals derived from non-invasive checks.
- Packages: installed package-manager inventory.
- Optimization: cleanup command previews with estimated space where detectable.
- Auto Fix: distro-aware install plans for missing tools.
- Reports: JSON, HTML, Markdown, PDF, and clipboard actions.
- Settings: theme and refresh controls for the running dashboard.
- Shortcuts: keyboard map for dashboard workflows.

## Safety

DevDoctor never runs install or cleanup commands automatically. The dashboard shows the exact command and lets the user copy it after review.

## Shortcuts

- `/`: search.
- `Tab`: switch pages.
- `Ctrl+R`: refresh checks.
- `Ctrl+E`: reports.
- `Ctrl+F`: Auto Fix.
- `Esc`: back.
- `Q`: quit.

## Classic Mode

Use `devdoctor --classic` to run the original Rich report flow.
