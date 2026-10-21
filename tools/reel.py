"""Records a Politics reel as an MP4, 30 frames a second, H.264.
It is 1080 × 1920 for Instagram Reels, or with --wide 1920 × 1080 for YouTube and LinkedIn.

The site draws every frame (static/js/lib/reel.js), so the reel looks like the site's charts.
This script opens the page in a headless browser, asks it for each frame in turn and hands the frames to ffmpeg.
Preview a reel first: open the same page with ?reel=1 in your browser.

Usage:
    .venv/bin/python tools/reel.py "https://data-mechanics.com/politics/brazil/?metric=gdp-per-capita&from=1990&to=2024"
    .venv/bin/python tools/reel.py "<page>" --output brazil-gdp.mp4
    .venv/bin/python tools/reel.py "<page>" --wide

It needs Playwright and its Chromium (pip install -r tools/requirements.txt, then playwright install chromium).
It also needs ffmpeg with libx264 on the PATH.
"""

import argparse
import base64
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

BATCH = 15  # frames per round trip to the page


def record_url(url, wide):
    """The page's address with ?reel=record, which draws frames on request instead of playing them.

    With `wide`, it also asks for the wide format (format=wide).
    """
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key not in ('reel', 'format')]
    query += [('reel', 'record')] + ([('format', 'wide')] if wide else [])
    return urlunsplit(parts._replace(query=urlencode(query)))


def encoder(output, fps):
    """ffmpeg, reading PNG frames on its input and writing an MP4 that Instagram takes as it is."""
    return subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'png', '-i', '-',
        # Flat colours and sharp edges, like a cartoon: x264's animation tuning keeps them clean.
        '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', '16', '-pix_fmt', 'yuv420p',
        # The frames are RGB and HD video is BT.709. The filter converts to it, and the stream says so, or phones shift the colours.
        '-vf', 'scale=out_color_matrix=bt709:out_range=tv',
        '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709',
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
        '-movflags', '+faststart', output,
    ], stdin=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description='Record a Politics reel as an MP4.')
    parser.add_argument('url', help='A Politics country page with the metric, measure and years you want.')
    parser.add_argument('--output', '-o', help='The MP4 to write (default: the name the page suggests).')
    parser.add_argument('--wide', action='store_true', help='1920 × 1080 for YouTube and LinkedIn, instead of a 1080 × 1920 reel.')
    args = parser.parse_args()
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg is not on the PATH.')

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        width, height = (1920, 1080) if args.wide else (1080, 1920)
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
        page.goto(record_url(args.url, args.wide), wait_until='networkidle')
        page.wait_for_function('window.reel?.ready === true', timeout=60_000)
        reel = page.evaluate('({ frames: reel.frames, fps: reel.fps, filename: reel.filename })')
        output = args.output or reel['filename']
        frames, fps = reel['frames'], reel['fps']
        print(f'{output}: {frames} frames, {frames / fps:.0f} s')

        video = encoder(output, fps)
        started = time.monotonic()
        for first in range(0, frames, BATCH):
            count = min(BATCH, frames - first)
            urls = page.evaluate('([first, count]) => Array.from({ length: count }, (_, i) => reel.frame(first + i))',
                                 [first, count])
            for url in urls:
                video.stdin.write(base64.b64decode(url.split(',', 1)[1]))
            print(f'\r{first + count} / {frames} frames', end='', flush=True)
        video.stdin.close()
        if video.wait():
            sys.exit('\nffmpeg failed.')
        browser.close()
    print(f'\nWrote {output} in {time.monotonic() - started:.0f} s.')


if __name__ == '__main__':
    main()
