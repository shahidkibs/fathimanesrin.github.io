"""Fetch the four supplied portfolio films and prepare browser-compatible media."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / 'assets' / 'videos'
FILE_IDS = [
    '1HoL49Br-3zMbCM3SDqO204FZGJkgIpme',
    '1BvBTyibPQAhNcbh-wHcRQEVmtgKZw5wP',
    '1hwaF66hq4qnYSxJidr9c6vwyoJZG8PCr',
    '19Ake09Q56qgBg8oJn3nM7thTA606Eh5F',
]

def prepare(item):
    number, file_id = item
    target = VIDEOS / f'video-{number:02}.mp4'
    poster = VIDEOS / f'video-{number:02}-poster.jpg'
    if target.exists() and poster.exists():
        print(f'Video {number}: already prepared', flush=True)
        return
    with tempfile.TemporaryDirectory() as tmp:
        original = Path(tmp) / 'original.mp4'
        url = 'https://drive.google.com/uc?' + urllib.parse.urlencode({'export': 'download', 'id': file_id})
        with urllib.request.urlopen(url, timeout=180) as response, original.open('wb') as output:
            shutil.copyfileobj(response, output)
        info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(original)]))
        assert any(s['codec_type'] == 'video' for s in info['streams']), f'File {number} is not a video'
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(original), '-map', '0:v:0', '-map', '0:a:0?']
        if number == 3:
            cmd += ['-vf', 'transpose=2', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy']
        else:
            cmd += ['-c', 'copy']
        subprocess.run(cmd + ['-movflags', '+faststart', str(target)], check=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', '1', '-i', str(target), '-frames:v', '1', '-vf', 'scale=960:960:force_original_aspect_ratio=decrease', '-q:v', '3', str(poster)], check=True)
        assert target.stat().st_size < 25 * 1024 * 1024
        print(f'Video {number}: prepared ({target.stat().st_size} bytes)', flush=True)

if __name__ == '__main__':
    VIDEOS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(prepare, enumerate(FILE_IDS, 1)))
