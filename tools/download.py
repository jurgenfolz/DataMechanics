"""Downloads a large file with curl, resuming a transfer that stalls or breaks, for the tools that build data/.

Some government sites stall and reset long downloads (bka.de, gov.br), and drop Python's connections.
"""

import subprocess
import sys

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
ATTEMPTS = 40


def download(url, path):
    """Saves `url` to `path`, resuming up to ATTEMPTS times, and returns the path."""
    for _ in range(ATTEMPTS):
        done = subprocess.run(['curl', '-sS', '-L', '-f', '-A', USER_AGENT, '-m', '300', '--speed-limit', '500',
                               '--speed-time', '20', '-C', '-', '-o', str(path), url])
        if done.returncode == 0:
            return path
    sys.exit(f'Could not download {url}')
