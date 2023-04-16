import os
import sys


def help():
    print("Sibyl static site generator")
    print("Usage: sibyl [command]")
    print("Commands:")
    print("  init - Initialize a new project")
    print("  dev - Start the development server")
    print("  build - Build the project")
    print("  help - Show this help message")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "dev":
                os.system("python -m sibyl.dev")
            elif sys.argv[1] == "build":
                os.system("python -m sibyl.build")
            elif sys.argv[1] == "init":
                os.system("python -m sibyl.init")
            elif sys.argv[1] == "help":
                help()
            else:
                print('Unknown command. Run "sibyl help" for more information.')
        else:
            os.system('Unknown command. Run "sibyl help" for more information.')
    except KeyboardInterrupt:
        os._exit(0)
