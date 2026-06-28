# Screenshot Assets

The files in this directory are generated from real DevDoctor CLI output.

- `terminal-preview.png`: static terminal preview generated from `devdoctor --quiet` and `devdoctor search docker --no-color`.
- `devdoctor-demo.gif`: short animated preview generated from the same command output.

Regenerate them after material CLI output changes:

```bash
mkdir -p assets/screenshots /tmp/devdoctor-demo
python -m devdoctor --quiet > /tmp/devdoctor-demo/frame1.txt
python -m devdoctor search docker --no-color | sed -n '1,26p' > /tmp/devdoctor-demo/frame2.txt
{
  printf 'DevDoctor v1.1.0\n\n'
  cat /tmp/devdoctor-demo/frame1.txt
  printf '\n'
  cat /tmp/devdoctor-demo/frame2.txt
} > /tmp/devdoctor-demo/terminal-preview.txt
convert -size 1320x860 xc:'#0B1020' -font DejaVu-Sans-Mono -pointsize 22 -fill '#E5EDF7' -annotate +48+64 '@/tmp/devdoctor-demo/terminal-preview.txt' assets/screenshots/terminal-preview.png
convert -delay 120 -loop 0 -size 1320x860 xc:'#0B1020' -font DejaVu-Sans-Mono -pointsize 24 -fill '#E5EDF7' -annotate +48+80 '@/tmp/devdoctor-demo/frame1.txt' -size 1320x860 xc:'#0B1020' -font DejaVu-Sans-Mono -pointsize 22 -fill '#E5EDF7' -annotate +48+64 '@/tmp/devdoctor-demo/frame2.txt' assets/screenshots/devdoctor-demo.gif
```

Use a clean terminal environment when preparing final marketing screenshots. Do not edit screenshots to show features that are not implemented.
