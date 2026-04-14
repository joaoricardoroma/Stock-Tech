import re

def resolve_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # We want to keep HEAD and remove origin/master.
    # The format is:
    # <<<<<<< HEAD
    # [HEAD content]
    # =======
    # [origin content]
    # >>>>>>> origin/master
    
    pattern = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n.*?>>>>>>> origin/master\n', re.DOTALL)
    new_content = pattern.sub(r'\1', content)
    
    with open(filepath, 'w') as f:
        f.write(new_content)

resolve_file('models.py')
resolve_file('app.py')
resolve_file('static/js/wine_stock.js')
