import sys
import os

from app import app
from database import check_superadmin_exists

def runserver(port=5000):
    print(f"\n=======================================================")
    print(f" Hospital Management System (HMS)")
    print(f" Server running at: http://127.0.0.1:{port}")
    print(f" Superadmin Email: admin@hms.com | Password: admin123")
    print(f"=======================================================\n")
    
    app.run(debug=True, host='127.0.0.1', port=port)

def main():
    args = sys.argv[1:]
    command = args[0] if args else 'runserver'

    if command == 'runserver':
        port = 5000
        if len(args) > 1:
            try:
                port_arg = args[1].split(':')[-1]
                port = int(port_arg)
            except ValueError:
                port = 5000
        runserver(port)
    elif command == 'shell':
        import code
        with app.app_context():
            code.interact(local=dict(globals(), **locals()))
    else:
        print(f"Unknown command '{command}'. Running server...")
        runserver()

if __name__ == '__main__':
    main()
