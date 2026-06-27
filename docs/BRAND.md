# Brand System

DevDoctor uses a calm, diagnostic visual system: dark workstation surfaces, cyan diagnostic light, and green recovery states.

## Assets

- Logo: `assets/brand/devdoctor-logo.svg`
- Logo PNG: `assets/brand/devdoctor-logo.png`
- App icon: `assets/brand/app-icon.svg`
- App icon PNG: `assets/brand/app-icon.png`
- Favicon: `assets/brand/favicon.svg`
- Favicon PNG: `assets/brand/favicon.png`
- GitHub social banner: `assets/brand/github-social-banner.png`
- Animated preview: `assets/brand/devdoctor-preview.gif`

## Color Palette

| Token | Hex | Use |
| --- | --- | --- |
| Night | `#0B1020` | App background |
| Panel | `#111827` | Cards and surfaces |
| Panel Elevated | `#101A2E` | Health and modal surfaces |
| Border | `#263A55` | Card borders |
| Diagnostic Cyan | `#22D3EE` | Primary accent |
| Glow Cyan | `#67E8F9` | Logo highlights and score emphasis |
| Recovery Green | `#34D399` | Passing states |
| Caution Amber | `#FBBF24` | Warning states |
| Failure Rose | `#FB7185` | Failure states |
| Text | `#E5EDF7` | Primary text |
| Muted | `#8EA4BD` | Secondary text |

## Typography

- Product and docs: Inter, Noto Sans, or Segoe UI.
- Terminal/code labels: JetBrains Mono, Noto Sans Mono, or the user's terminal monospace.
- Terminal UI should not use viewport-scaled font sizes; rely on spacing, borders, and color hierarchy.

## Voice

DevDoctor sounds direct and operational:

- Prefer: "Docker daemon is not reachable."
- Avoid: "Critical threat detected."
- Prefer: "Review Command."
- Avoid: "Run magic fix."

## Interface Rules

- Health score is the primary visual anchor.
- Prefer compact cards over dense tables in the dashboard.
- Export and install actions must show exact file paths or commands.
- Destructive or privileged actions are preview-only and require explicit user action outside automatic scans.
- Use icons sparingly: `✓` pass, `⚠` warning, `✕` failure, `◆` brand mark.

