from pathlib import Path

path = Path( sweepstake.py)
text = path.read_text(encoding= utf-8)
marker =  import pandas as pd\n
if  \nimport altair as alt\n not in text and marker in text:
    text = text.replace(marker, marker +  import altair as alt\n, 1)

