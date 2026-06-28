# Brand System

DevDoctor uses a calm workstation-bootstrap identity: dark terminal surfaces, cyan diagnostics, green ready states, amber repair states, and rose missing states.

## Assets

- Logo: `assets/brand/devdoctor-logo.svg`
- Logo PNG: `assets/brand/devdoctor-logo.png`
- App icon: `assets/brand/app-icon.svg`
- App icon PNG: `assets/brand/app-icon.png`
- Favicon: `assets/brand/favicon.svg`
- Favicon PNG: `assets/brand/favicon.png`
- GitHub social banner: `assets/brand/github-social-banner.png`

## Color Palette

| Token | Hex | Use |
| --- | --- | --- |
| Night | `#0B1020` | Background |
| Panel | `#111827` | Terminal panels and report surfaces |
| Border | `#263A55` | Table and panel borders |
| Diagnostic Cyan | `#22D3EE` | Primary accent |
| Glow Cyan | `#67E8F9` | Logo highlight |
| Ready Green | `#34D399` | Installed states |
| Repair Amber | `#FBBF24` | Broken or repairable states |
| Missing Rose | `#FB7185` | Missing states |
| Text | `#E5EDF7` | Primary text |
| Muted | `#8EA4BD` | Secondary text |

## Typography

- Product and docs: Inter, Noto Sans, Segoe UI, or the system UI font.
- Terminal/code labels: JetBrains Mono, Noto Sans Mono, or the user's terminal monospace.
- Do not scale terminal text with viewport width.

## Voice

DevDoctor sounds direct and operational.

- Prefer: "Docker is missing. Install plan: sudo dnf install moby-engine."
- Avoid: "Critical environment failure detected."
- Prefer: "No changes made. Use --apply to execute commands."
- Avoid: "Magic repair complete."

## Interface Rules

- Installed, missing, and broken counts are the primary visual anchors.
- Use tables for comparable command data.
- Always show exact commands before system changes.
- Do not imply a command ran unless DevDoctor actually executed it.
- Do not invent download sizes, latest versions, or package ownership data.
