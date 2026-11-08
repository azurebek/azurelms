# Figtree font source

- Official repository: <https://github.com/erikdkennedy/figtree>
- Source commit: `032dfa7fe219ef3a02890d6d3add84eacc9aebfe`
- Files: `fonts/webfonts/Figtree-Regular.woff2`, `Figtree-Medium.woff2`, `Figtree-SemiBold.woff2`
- License: SIL Open Font License 1.1; the official upstream `OFL.txt` text is included here
  (one trailing space was normalized for the repository whitespace check).

Only the 400, 500 and 600 upright weights required by DESIGN-02 are vendored.

The upstream files contain Turkish letters and the U+2018/U+2019 quote marks used by AzureLMS UI copy.
They do not encode U+02BB/U+02BC; user-entered variants therefore use the declared system-font fallback,
while search normalization continues to treat all apostrophe variants as equivalent.
