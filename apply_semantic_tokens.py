import os, glob

template_dir = r"c:\projects\azure_lms\templates"
files = glob.glob(os.path.join(template_dir, "**/*.html"), recursive=True)

replacements = {
    'var(--bg-color)': 'var(--bg-body)',
    'var(--card-bg)': 'var(--bg-surface)',
    'var(--nav-bg)': 'var(--bg-surface)',
    'var(--input-bg)': 'var(--bg-surface)',
    'var(--text-color)': 'var(--text-main)',
    'var(--primary-color)': 'var(--accent-color)',
    'text-dark': '',  # Removing hardcoded classes
    'bg-light': '',
    'border-secondary': ''
}

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for old, new in replacements.items():
        # Only replace class occurrences carefully to avoid breaking substrings
        if old in ['text-dark', 'bg-light', 'border-secondary']:
            # replace class exact matches
            content = content.replace(f' {old}', '')
            content = content.replace(f'class="{old} ', 'class="')
            content = content.replace(f'class="{old}"', 'class=""')
        else:
            content = content.replace(old, new)
            
    if content != original_content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
            
print('Semantic tokens applied successfully across all templates!')
