import os
import re

def check_templates_for_typography():
    """Check all HTML templates for typography.css inclusion."""
    templates_dir = 'templates'
    missing_typography = []
    
    # Walk through the templates directory
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check if typography.css is included
                    if 'typography.css' not in content:
                        missing_typography.append(filepath)
    
    # Print results
    print(f"Templates missing typography.css: {len(missing_typography)}")
    for template in missing_typography:
        print(f" - {template}")
        
    return missing_typography

def add_typography_to_templates(templates):
    """Add typography.css link to templates that are missing it."""
    for template in templates:
        with open(template, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find where colours.css is included and add typography after it
        if 'colours.css' in content:
            content = content.replace(
                '<link href="/static/colours.css" rel="stylesheet">',
                '<link href="/static/colours.css" rel="stylesheet">\n  <link href="/static/typography.css" rel="stylesheet">'
            )
        # If no colours.css, try to add after bootstrap
        elif 'bootstrap' in content:
            content = content.replace(
                'bootstrap.min.css" rel="stylesheet">',
                'bootstrap.min.css" rel="stylesheet">\n  <link href="/static/typography.css" rel="stylesheet">'
            )
        
        # Write updated content
        with open(template, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Added typography.css to {template}")

if __name__ == "__main__":
    missing = check_templates_for_typography()
    if missing:
        add_typography_to_templates(missing)
        print("Added typography.css to all missing templates.")
    else:
        print("All templates already include typography.css!")