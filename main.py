from typing import Union, Annotated
from yt_dlp import YoutubeDL
from fastapi import FastAPI, responses, Header, HTTPException
import pyotp
from dotenv import load_dotenv, dotenv_values

load_dotenv()
config = dotenv_values('.env')
app = FastAPI()

def check_video_id(video_id: str):
    if video_id is None: return False
    # check if video_id is url
    if video_id.startswith('https://www.youtube.com/watch?v='):
        video_id = video_id.split('https://www.youtube.com/watch?v=')[1]
    # check if video_id is valid
    if len(video_id) != 11:
        return False
    return True

async def get_yt_filename(video_id: str, ydl: YoutubeDL):
    info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
    file_name = ydl.prepare_filename(info)
    file_name = (file_name.split('.')[:-1] + ['.mp3'])
    file_name = ''.join(file_name)
    return file_name

@app.get("/")
def read_root():
    return {"Hello": "World"} 

@app.get("/yt/audio")
async def get_yt(id: str, otp: Annotated[str, Header()]):
    password = config['PASSWORD']
    totp = pyotp.TOTP(password)
    if totp.verify(otp):
        print('OTP Verified')
    else:
        raise HTTPException(status_code=401, detail='Invalid OTP')
    if check_video_id(id) is False:
        raise HTTPException(status_code=400, detail='Invalid Video ID')
    if id.startswith('https://www.youtube.com/watch?v='):
        id = id.split('https://www.youtube.com/watch?v=')[1]

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s-%(format_id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'ffmpeg-location': 'ffmpeg'
    }

    with YoutubeDL(ydl_opts) as ydl:
        file_name = await get_yt_filename(id, ydl)
        print(file_name)
        ydl.download([f'https://www.youtube.com/watch?v={id}'])
    return responses.FileResponse(file_name, media_type='application/octet-stream', filename=file_name)