import sys
import os
import shutil

def show_help():
    sys.stderr.write('To use this script, attach files to the email and send with the subject savefiles')
    sys.exit(0)

if __name__ == '__main__':
    if sys.argv[4].upper().find('HELP') != -1:
        show_help()

if len(sys.argv) != 6:
    sys.stderr.write('No files were attached. Nothing was saved.\n')

files = eval(sys.argv[5])

for name, path in files:
    new_location = os.path.join(os.environ['HOME'] + '/Downloads', name)
    shutil.move(path, new_location)
    sys.stderr.write('{0} was saved to {1}\n', name, new_location)
