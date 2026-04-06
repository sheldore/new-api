"""Deprecated: use deploy/deploy.py artifact deployment instead."""
import sys


def main():
    print('❌ This deploy entrypoint is deprecated.')
    print('Use: python deploy/deploy.py /path/to/neo-api-dreamfac.tar.gz')
    sys.exit(1)


if __name__ == '__main__':
    main()
