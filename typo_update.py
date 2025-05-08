import os
import re
from bs4 import BeautifulSoup

def apply_typography_classes():
    """Apply typography classes to HTML elements in templates."""
    templates_dir = 'templates'
    updated_files = []
    
    # Walk through the templates directory
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                updated = update_typography_in_file(filepath)
                if updated:
                    updated_files.append(filepath)
    
    # Print results
    print(f"Updated typography in {len(updated_files)} templates:")
    for template in updated_files:
        print(f" - {template}")

def update_typography_in_file(filepath):
    """Update typography classes in a specific HTML file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use Beautiful Soup for safer HTML parsing
        soup = BeautifulSoup(content, 'html.parser')
        
        changes_made = False
        
        # Apply typography classes to headings if they don't already have them
        for heading_level in range(1, 7):
            for heading in soup.find_all(f'h{heading_level}'):
                if not heading.has_attr('class') or 'h{heading_level}' not in heading.get('class'):
                    if not heading.has_attr('class'):
                        heading['class'] = []
                    heading['class'].append(f'h{heading_level}')
                    changes_made = True
        
        # Apply text size classes based on element types
        # For paragraphs with no class, apply text-sm
        for p in soup.find_all('p'):
            if not p.has_attr('class'):
                p['class'] = ['text-sm']
                changes_made = True
        
        # For text in alert boxes, apply text-sm
        for alert in soup.find_all(class_=re.compile(r'alert')):
            for p in alert.find_all('p'):
                if not p.has_attr('class'):
                    p['class'] = ['text-sm', 'mb-1']
                    changes_made = True
        
        # For labels, apply font-medium
        for label in soup.find_all('label'):
            if not label.has_attr('class') or 'font-medium' not in label.get('class'):
                if not label.has_attr('class'):
                    label['class'] = []
                label['class'].append('font-medium')
                changes_made = True
        
        # Write updated content if changes were made
        if changes_made:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

if __name__ == "__main__":
    apply_typography_classes()