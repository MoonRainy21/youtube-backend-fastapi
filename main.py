from typing import Union, Annotated
from yt_dlp import YoutubeDL
from fastapi import FastAPI, responses, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pyotp
from dotenv import load_dotenv, dotenv_values
import zipfile
import os

load_dotenv()
config = dotenv_values('.env')
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_video_id(video_id: str):
    if video_id is None: return False
    # check if video_id is url
    if video_id.startswith('https://www.youtube.com/watch?v='):
        video_id = video_id.split('https://www.youtube.com/watch?v=')[1]
    # check if video_id is valid
    if len(video_id) != 11:
        return False
    return True

async def get_yt_filename(video_id: str, ydl: YoutubeDL, ext: str):
    info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
    file_name = ydl.prepare_filename(info)
    file_name = (file_name.split('.')[:-1] + [ext])
    file_name = ''.join(file_name)
    return file_name

@app.get("/")
def read_root():
    return {"Hello": "World"} 

@app.get("/yt/audio")
async def get_yt(id: str, otp: Annotated[str, Header()]=None):
    password = config['PASSWORD']
    totp = pyotp.TOTP(password)
    if totp.verify(otp) or True:
        print('OTP Verified')
    else:
        raise HTTPException(status_code=401, detail='Invalid OTP')
    if check_video_id(id) is False:
        raise HTTPException(status_code=400, detail='Invalid Video ID')
    if id.startswith('https://www.youtube.com/watch?v='):
        id = id.split('https://www.youtube.com/watch?v=')[1]

    # if the file already exists, return it
    if os.path.exists(f'downloads/{id}-audio.mp3'):
        return responses.FileResponse(f'downloads/{id}-audio.mp3', media_type='application/octet-stream', filename=f'{id}-audio.mp3')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s-%(format_id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    with YoutubeDL(ydl_opts) as ydl:
        file_name = await get_yt_filename(id, ydl, '.mp3')
        print(file_name)
        ydl.download([f'https://www.youtube.com/watch?v={id}'])
    # rename the downloaded file
    new_file_name = 'downloads/'+id+'-audio'+'.mp3'
    os.rename(file_name, new_file_name)
    return responses.FileResponse(new_file_name, media_type='application/octet-stream', filename=new_file_name)

@app.get("/yt/video")
async def get_yt_video(id: str, otp: Annotated[str, Header()]):
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
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(title)s-%(format_id)s.mp4'
    }

    with YoutubeDL(ydl_opts) as ydl:
        file_name = await get_yt_filename(id, ydl, 'mp4')
        print(file_name)
        ydl.download([f'https://www.youtube.com/watch?v={id}'])
    return responses.FileResponse(file_name, media_type='application/octet-stream', filename=file_name)

@app.get("/yt/playlist-audio")
async def get_yt_playlist(id: str, otp: Annotated[str, Header()]):
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
        }]
    }

    files = []
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'https://www.youtube.com/playlist?list={id}', download=False)
        title = info['title']
        for video in info['entries']:
            file_name = await get_yt_filename(video['id'], ydl, 'mp3')
            files.append(file_name)
            ydl.download([f'https://www.youtube.com/watch?v={video["id"]}'])
    
    # zip files
    zip_file_name = f'{title}.zip'
    with zipfile.ZipFile(zip_file_name, 'w') as zip:
        for file in files:
            zip.write(file)
    return responses.FileResponse(zip_file_name, media_type='application/octet-stream', filename=zip_file_name)