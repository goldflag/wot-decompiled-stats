Tank stats extracted from https://github.com/IzeBerg/wot-src/tree/f3deb5e97288664b1e17b2df6887d526b7ad4940

Built using Python 3.11.9

# Scripts

## xml_processor.py

Processes XML files into tank stats

### Run

1. Set environment variable `API_KEY` to your Wargaming API key
2. Initialize Python virtual environment `python -m venv venv` (optional)
3. Install dependencies `pip install -r requirements.txt`
4. Run script `python xml_processor.py`

## model_processor.py

Converts tank models into `.glb`. This script generates up to 70gb of files, so make sure you have enough disk space. It can also take hours to finish.

### Run

1. Must be on Windows
2. Install Blender 3.6.0 and `bpy` 3.6.0
3. Add Blender to your system PATH environment variable (most likely `C:\Program Files\Blender Foundation\Blender 3.6`)
4. Add Blender to your system PATH environment variable (most likely `C:\Program Files\Blender Foundation\Blender 3.6`)
5. Initialize Python virtual environment `python -m venv venv` (optional)
6. Install dependencies `pip install -r requirements.txt`
7. Run script `python model_processor.py`
