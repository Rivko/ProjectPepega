# How to setup:
1) Install python https://www.python.org/downloads/
2) Download this repo
3) Open terminal in repo folder
4) Type `pip install -r requirements.txt`
5) Open `config.py` and change settings

# If you want to patch a library with values from spreadsheet:
1) Put a stock library (or any library that you want to use as a base) in the main folder
2) Change the `SPREADSHEET_URL`, `SHEET_NAME` and `LIB_TO_PATCH` values in `config.py`
3) Run `python patch.py`
4) Patched library will appear in `/patched/` folder along with generated changelog.

# If you want to convert a .hbk bookmark file:
1) Put your .hbk and stock library in the main folder
2) Change the `HBK_NAME` and `LIB_TO_EXTRACT` values in `config.py`
3) Run `python convert.py`
4) Import generated .csv file into an already set up google spreadsheet as a new sheet
![1](https://user-images.githubusercontent.com/2606215/148261274-36ee25e8-11ad-4985-abf1-ccb7d6f061e0.png)


