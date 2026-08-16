# ShellCode Updater Updater

## Run

```powershell
pip install -r requirements.txt
python app.py
```

Open:

http://127.0.0.1:5000

The filename byte output is explicitly returned by Flask as `filename_bytes`
and rendered by the web page as `data.filename_bytes`.

Example:

`libvischk.so`

becomes:

`0x6C, 0x69, 0x62, 0x76, 0x69, 0x73, 0x63, 0x68, 0x6B, 0x2E, 0x73, 0x6F, 0x00`
