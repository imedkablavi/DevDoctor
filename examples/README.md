# DevDoctor Examples

These examples use real DevDoctor commands. Output varies by distribution, installed package managers, PATH, and local tools.

## Inventory

```bash
devdoctor
devdoctor --quiet
devdoctor --json | python -m json.tool
```

Expected compact output shape:

```text
installed=35 missing=33 warnings=26 broken=0 total=68
```

## Check Tools

```bash
devdoctor check git docker node
devdoctor check --profile devops --missing
devdoctor check --category cloud-clis
```

Use `--missing` when onboarding a workstation and you only want install plans.

## Search Catalog

```bash
devdoctor search docker
devdoctor search python
devdoctor list tools --category containers
```

Search shows catalog details, local health state, profiles, dependencies, and install commands when available.

## Install Planning

```bash
devdoctor install git docker
devdoctor install git docker --dry-run
devdoctor install --profile frontend --dry-run
```

No packages are installed unless `--apply` is passed. Without `--yes`, DevDoctor asks before each command.

## Repair Suggestions

```bash
devdoctor repair
devdoctor repair docker
devdoctor repair --profile flutter
```

Repair is read-only. It prints the problem, reason, risk, repair command or manual action, and verification command when available.

## Verification

```bash
devdoctor verify --profile general
devdoctor verify git python docker --quiet
```

`verify` exits with code `1` when selected tools are missing, warning, or broken. Use this in onboarding scripts when a non-ready workstation should fail the step.

## Export

```bash
devdoctor --json-file inventory.json
devdoctor --markdown-file inventory.md
devdoctor --html-file inventory.html
devdoctor export json --output inventory.json
devdoctor export markdown --output inventory.md
```

JSON is the stable machine-readable format. Markdown is useful for issues, pull requests, and handoff notes.

## Maintenance Commands

```bash
devdoctor update
devdoctor cache clean
devdoctor uninstall docker
devdoctor self-update
```

These commands preview operations. Add `--apply` only after reviewing the commands.

## Legacy Health Report

```bash
devdoctor health --quiet
devdoctor health --json
devdoctor health --html-file health.html
devdoctor health --pdf-file health.pdf
```

The legacy health report remains for users that need the older check/export model.
