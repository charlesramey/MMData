# Build Instructions

`pyinstaller --noconsole --onedir --clean \
--name "MMData" \
--exclude-module torch \
--exclude-module tensorflow \
--exclude-module IPython \
MMData.py`
